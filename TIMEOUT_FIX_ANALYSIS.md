# Timeout Hang Issue - Root Cause Analysis & Fix

## Problem Statement
When the script connects to an endpoint that doesn't respond to SSH, it hangs for approximately **1 minute** before timing out, despite timeout values being set to **10 seconds** in both environment variables and default values.

---

## Root Cause Analysis

### Why the 1-Minute Hang?

The hang occurs due to **three independent timeout mechanisms** in Paramiko/Netmiko, each with their own defaults:

#### 1. **TCP Connection Timeout (OS Level)**
- **When:** Initial TCP SYN to an unresponsive endpoint
- **Controlled by:** Paramiko's `SSHClient.connect(timeout=...)` parameter
- **Status in Your Code:** ✅ Correctly set to 10 seconds
- **Problem:** Limited to initial TCP handshake only

#### 2. **SSH Protocol Timeouts (Paramiko Transport Level)**
- **banner_timeout:** Wait for SSH banner from server (default: 15s)
- **auth_timeout:** Wait for authentication response (default: 30s)
- **Status in Your Code:** ✅ Correctly set to 10 seconds
- **Problem:** These only apply AFTER TCP connection succeeds

#### 3. **SSH Channel Operation Timeout (Critical!)**
- **When:** Opening a new channel (e.g., `direct-tcpip` for jump server tunneling)
- **Controlled by:** Paramiko's `channel_timeout` parameter on Transport
- **Default Value:** **3600 seconds (1 hour)** if not specified!
- **Status in Your Code:** ❌ **NOT SET** — causing the hang
- **Problem:** When calling `transport.open_channel("direct-tcpip", ...)` without a timeout, it defaults to 1 hour

#### 4. **Socket Timeout on Jump Client Transport**
- **When:** After Transport is created by `SSHClient.connect()`
- **What Happens:** Paramiko **overwrites** the socket timeout to ~0.2s for internal activity checks
- **Status in Your Code:** ❌ **NOT SET** — only internal checks can timeout
- **Problem:** No explicit socket timeout on the jump client's underlying socket after connection

---

## How the Hang Happens (Flow)

```
1. Worker thread tries to connect via jump server to unresponsive target (e.g., 10.1.1.1)
   ↓
2. Paramiko connects to jump server ✅ (timeout=10s works here)
   ↓
3. Worker calls: transport.open_channel("direct-tcpip", dest_addr=(10.1.1.1, 22))
   ↓
4. Paramiko tries to establish tunnel to unresponsive target
   ↓
5. TCP SYN packet sent, but target doesn't respond
   ↓
6. OS retries TCP connection (typically 6 retries over ~60 seconds)
   ↓
7. Paramiko's channel_timeout is 3600s (NOT overridden), so it waits indefinitely
   ↓
8. After ~60 seconds, OS gives up on TCP retries → finally times out
   ↓
9. Exception is caught, worker moves to next device
   ↓
10. Repeat for each unresponsive device → slow discovery process
```

---

## Solution Implemented

Three targeted fixes were applied to `main.py`:

### Fix #1: Add `channel_timeout` Parameter to Jump Client Connection
**Location:** `_paramiko_jump_client()` method

```python
client.connect(
    hostname=jump_host,
    username=username,
    password=password,
    look_for_keys=False,
    allow_agent=False,
    banner_timeout=self.timeout,
    auth_timeout=self.timeout,
    timeout=self.timeout,
    channel_timeout=self.timeout,  # ← NEW: Limit channel operations timeout
)
```

**Effect:** Sets Paramiko Transport's `channel_timeout` to your configured timeout value (10s), preventing it from defaulting to 3600s.

### Fix #2: Set Socket Timeout on Jump Client Transport
**Location:** `_paramiko_jump_client()` method (after `connect()`)

```python
try:
    transport = client.get_transport()
    if transport and transport.sock:
        transport.sock.settimeout(self.timeout)  # ← NEW: Force socket timeout
        logger.debug("Set socket timeout to %d seconds for jump host %s", self.timeout, jump_host)
except Exception as e:
    logger.debug("Could not set socket timeout on jump client: %s", e)
```

**Effect:** 
- Overrides Paramiko's internal ~0.2s socket timeout 
- Catches TCP-level hangs from unresponsive targets
- Falls back gracefully if socket is unavailable

### Fix #3: Add `timeout` Parameter to `open_channel()` Call
**Location:** `_netmiko_via_jump()` method

```python
channel = transport.open_channel(
    "direct-tcpip", 
    dest_addr, 
    local_addr, 
    timeout=self.timeout  # ← NEW: Explicit timeout on channel open
)
```

**Effect:** Enforces your configured timeout (10s) on the channel opening process itself, preventing 1-hour waits.

---

## Expected Behavior After Fix

### Before Fix
- Unresponsive endpoint → ~60 second hang → times out
- 20 unresponsive endpoints → ~20 minutes of waiting on TCP retries alone

### After Fix
- Unresponsive endpoint → ~10 second timeout → continues to next device
- 20 unresponsive endpoints → ~200 seconds total (10s × 20) + processing

**Time saved:** ~80% reduction in discovery time when encountering unresponsive devices

---

## Timeout Configuration Reference

Your script now respects these timeout hierarchies:

### Jump Server Connection
1. **TCP connect + banner:** `timeout=10s` (SSHClient.connect)
2. **Authentication:** `auth_timeout=10s`
3. **Channel operations:** `channel_timeout=10s`
4. **Socket operations:** `sock.settimeout(10s)`

### Target Device (via jump)
1. **SSH handshake:** Handled by Netmiko's `auth_timeout=10s`, `banner_timeout=10s`
2. **Command execution:** `read_timeout=10s` on `send_command()`

### Target Device (direct)
1. **Connection:** `conn_timeout=10s`
2. **SSH handshake:** `auth_timeout=10s`, `banner_timeout=10s`
3. **Command execution:** `read_timeout=10s` on `send_command()`

---

## Environment Variables Still Supported

You can override default timeout via:
```bash
# Set to 15 seconds
export CDP_TIMEOUT=15

# Set to 5 seconds (for faster failure on slow networks)
export CDP_TIMEOUT=5
```

All three timeout mechanisms will respect your configured value.

---

## Testing Recommendations

To verify the fix works:

1. **Test with truly unresponsive IP:**
   ```powershell
   $env:CDP_TIMEOUT = 10
   python main.py
   # At prompt, enter a seed IP of a non-existent device (e.g., 192.0.2.1)
   ```
   - **Expected:** Should timeout in ~10 seconds, not ~60 seconds

2. **Monitor logs:**
   ```
   "Set socket timeout to 10 seconds for jump host ..."
   "[10.1.1.X] Attempt 1: collecting CDP + version"
   "[10.1.1.X] Connection issue: ..."  # Should appear after ~10s
   ```

3. **Measure time:**
   ```powershell
   $timer = [System.Diagnostics.Stopwatch]::StartNew()
   python main.py
   # ... enter seeds, provide credentials ...
   $timer.Stop()
   Write-Host "Total discovery time: $($timer.ElapsedSeconds) seconds"
   ```

---

## Technical Details

### Paramiko Timeout Parameters Explained

| Parameter | Where | Default | Purpose |
|-----------|-------|---------|---------|
| `timeout` | SSHClient.connect() | 30s | TCP connection + SSH banner timeout |
| `banner_timeout` | SSHClient.connect() | 15s | SSH banner reception timeout |
| `auth_timeout` | SSHClient.connect() | 30s | Authentication response timeout |
| `channel_timeout` | SSHClient.connect() + Transport | **3600s** | Channel opening (e.g., direct-tcpip) timeout |
| `sock.settimeout()` | Transport.sock | ~0.2s (internal) | Raw socket read/write timeout |

### Why `channel_timeout` Matters for Jump Servers

When using `direct-tcpip` (SSH tunneling), Paramiko needs to:
1. Send a `SSH_MSG_CHANNEL_OPEN` request to jump server
2. Wait for jump server to accept and open tunnel to target
3. Jump server attempts TCP connection to target IP:22
4. **If target is unresponsive:** Jump server waits for its own TCP timeout
5. **Without `channel_timeout`:** Paramiko client waits up to 3600s for jump server response

**Our fix:** Limits to 10s, so client doesn't wait for OS-level TCP retries (which take ~60s anyway).

---

## Files Modified

- `main.py` - `_paramiko_jump_client()` method (2 changes)
- `main.py` - `_netmiko_via_jump()` method (1 change)

Total lines changed: ~8 lines (3 fixes + comments)

---

## Backwards Compatibility

✅ **Fully backwards compatible**
- All changes are additive (new parameters)
- Existing error handling unchanged
- Falls back gracefully if socket timeout can't be set
- No breaking changes to API or signatures

---

## Performance Impact

- **Negligible:** Socket timeout setting is a single syscall per jump server connection
- **Logging:** Debug-level log entries (no performance impact at INFO level)
- **Benefit:** 80% reduction in hang time for unresponsive endpoints

---

## Future Improvements (Optional)

If you want even faster timeouts for network paths with higher latency:

```python
# Set per-environment variable (in addition to CDP_TIMEOUT)
export CDP_CHANNEL_TIMEOUT=5  # Faster channel open timeout
export CDP_SOCKET_TIMEOUT=5   # Faster socket timeout
```

Implementation would be straightforward in the `_paramiko_jump_client()` method.

---

## Summary

**The Problem:** Paramiko's `channel_timeout` defaulted to 1 hour, causing 60-second hangs on unresponsive endpoints.

**The Solution:** 
1. Set `channel_timeout=self.timeout` on jump client connection ✅
2. Set `transport.sock.settimeout(self.timeout)` after connection ✅
3. Pass `timeout=self.timeout` to `open_channel()` ✅

**The Result:** ~60 second hangs reduced to ~10 seconds per unresponsive device.
