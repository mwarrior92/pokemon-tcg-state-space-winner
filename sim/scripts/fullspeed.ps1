# Let a running simulator process use the performance cores.
#
#   powershell -ExecutionPolicy Bypass -File sim/scripts/fullspeed.ps1 [-ProcessId <pid>] [-Match <command-line text>]
#
# Windows 11 treats a windowless background process as low priority ("power throttling" /
# efficiency mode) and runs it on the efficiency cores only: on the i7-13650HX the 8 E-cores sat at
# 100% while the 6 P-cores (12 threads) idled, so more workers never helped. This turns power
# throttling off for the process (all its worker threads) and raises it to Above normal priority.
# It changes only that process and ends with it; no admin rights, no system setting.
param([int]$ProcessId = 0, [string]$Match = 'sim[\\/]dist')

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class Throttle {
  [StructLayout(LayoutKind.Sequential)]
  public struct PROCESS_POWER_THROTTLING_STATE { public uint Version; public uint ControlMask; public uint StateMask; }
  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern bool SetProcessInformation(IntPtr h, int infoClass, ref PROCESS_POWER_THROTTLING_STATE info, uint size);
  [DllImport("kernel32.dll")]
  public static extern bool CloseHandle(IntPtr h);
  public static bool Off(int pid) {
    IntPtr h = OpenProcess(0x0200 /* PROCESS_SET_INFORMATION */, false, pid);
    if (h == IntPtr.Zero) return false;
    var s = new PROCESS_POWER_THROTTLING_STATE { Version = 1, ControlMask = 0x1 | 0x4 /* EXECUTION_SPEED | IGNORE_TIMER_RESOLUTION */, StateMask = 0 };
    bool ok = SetProcessInformation(h, 4 /* ProcessPowerThrottling */, ref s, (uint)Marshal.SizeOf(s));
    CloseHandle(h);
    return ok;
  }
}
"@

$targets = if ($ProcessId) { @(Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId") }
           else { @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match $Match }) }
foreach ($p in $targets) {
  $ok = [Throttle]::Off([int]$p.ProcessId)
  try { (Get-Process -Id $p.ProcessId).PriorityClass = 'AboveNormal' } catch {}
  "{0}: power throttling off = {1}; {2}" -f $p.ProcessId, $ok, $p.CommandLine.Substring(0, [math]::Min(120, $p.CommandLine.Length))
}
if (-not $targets) { "no matching process" }
