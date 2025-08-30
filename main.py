#!/usr/bin/env python3
"""
Smart System Monitor & Greeting Tool
Collects system information and generates intelligent greetings based on system health
"""

import os
import sys
import json
import time
import platform
import subprocess
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

try:
    import psutil
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.layout import Layout
    from rich import box
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install psutil rich")
    sys.exit(1)

class SystemMonitor:
    """Cross-platform system information collector"""
    
    def __init__(self):
        self.os_type = platform.system().lower()
        self.console = Console()
        
    def get_storage_info(self) -> Dict[str, Any]:
        """Get disk usage information"""
        try:
            if self.os_type == "windows":
                disk = psutil.disk_usage('C:')
            else:
                disk = psutil.disk_usage('/')
            
            used_gb = disk.used / (1024**3)
            total_gb = disk.total / (1024**3)
            free_gb = disk.free / (1024**3)
            
            return {
                "used_gb": round(used_gb, 2),
                "total_gb": round(total_gb, 2),
                "free_gb": round(free_gb, 2),
                "percent_used": round(disk.percent, 1),
                "status": "low" if disk.percent > 85 else "normal"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory usage information"""
        try:
            memory = psutil.virtual_memory()
            
            return {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": round(memory.percent, 1),
                "status": "high" if memory.percent > 80 else "normal"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_startup_info(self) -> Dict[str, Any]:
        """Get system startup time and uptime"""
        try:
            boot_time = psutil.boot_time()
            startup_time = datetime.fromtimestamp(boot_time)
            uptime = datetime.now() - startup_time
            
            return {
                "startup_time": startup_time.strftime("%Y-%m-%d %H:%M:%S"),
                "uptime_hours": round(uptime.total_seconds() / 3600, 1),
                "uptime_days": uptime.days,
                "status": "long" if uptime.days > 7 else "normal"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_autostart_programs(self) -> List[str]:
        """Get list of autostart programs (OS-specific)"""
        programs = []
        
        try:
            if self.os_type == "windows":
                programs.extend(self._get_windows_autostart())
            elif self.os_type == "linux":
                programs.extend(self._get_linux_autostart())
            elif self.os_type == "darwin":
                programs.extend(self._get_macos_autostart())
        except Exception as e:
            programs.append(f"Error detecting autostart: {str(e)}")
        
        return programs[:10]
    
    def _get_windows_autostart(self) -> List[str]:
        """Get Windows autostart programs from registry"""
        programs = []
        try:
            import winreg
            
            keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")
            ]
            
            for hkey, subkey in keys:
                try:
                    key = winreg.OpenKey(hkey, subkey)
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            programs.append(name)
                            i += 1
                        except WindowsError:
                            break
                    winreg.CloseKey(key)
                except:
                    continue
        except ImportError:
            try:
                result = subprocess.run(
                    ['reg', 'query', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if 'REG_' in line:
                        parts = line.strip().split()
                        if parts:
                            programs.append(parts[0])
            except:
                pass
        
        return programs
    
    def _get_linux_autostart(self) -> List[str]:
        """Get Linux autostart programs from .desktop files"""
        programs = []
        autostart_dirs = [
            Path.home() / ".config" / "autostart",
            Path("/etc/xdg/autostart")
        ]
        
        for autostart_dir in autostart_dirs:
            if autostart_dir.exists():
                for desktop_file in autostart_dir.glob("*.desktop"):
                    try:
                        with open(desktop_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            for line in content.split('\n'):
                                if line.startswith('Name='):
                                    programs.append(line.split('=', 1)[1])
                                    break
                    except:
                        continue
        
        return programs
    
    def _get_macos_autostart(self) -> List[str]:
        """Get macOS login items"""
        programs = []
        try:
            result = subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to get the name of every login item'],
                capture_output=True, text=True, timeout=10
            )
            if result.stdout:
                programs = [item.strip() for item in result.stdout.split(',')]
        except:
            pass
        
        return programs
    
    def get_running_services(self) -> List[str]:
        """Get critical running services"""
        services = []
        
        try:
            if self.os_type == "windows":
                result = subprocess.run(
                    ['sc', 'query', 'type=', 'service', 'state=', 'running'],
                    capture_output=True, text=True, timeout=15
                )
                for line in result.stdout.split('\n'):
                    if 'SERVICE_NAME:' in line:
                        service_name = line.split(':', 1)[1].strip()
                        services.append(service_name)
            
            elif self.os_type == "linux":
                result = subprocess.run(
                    ['systemctl', 'list-units', '--type=service', '--state=running', '--no-legend'],
                    capture_output=True, text=True, timeout=15
                )
                for line in result.stdout.split('\n'):
                    if line.strip():
                        service_name = line.split()[0].replace('.service', '')
                        services.append(service_name)
                        
        except Exception as e:
            services.append(f"Error: {str(e)}")
        
        return services[:8]
    
    def get_battery_info(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive battery information if available"""
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return None
            
            battery_info = {
                "percent": battery.percent,
                "plugged": battery.power_plugged,
                "time_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None,
                "status": "critical" if battery.percent < 20 and not battery.power_plugged else "normal"
            }
            
            battery_health = self._get_detailed_battery_health()
            if battery_health:
                battery_info.update(battery_health)
            
            return battery_info
        except:
            pass
        return None
    
    def _get_detailed_battery_health(self) -> Optional[Dict[str, Any]]:
        """Get detailed battery health information (OS-specific)"""
        health_info = {}
        
        try:
            if self.os_type == "windows":
                health_info.update(self._get_windows_battery_health())
            elif self.os_type == "linux":
                health_info.update(self._get_linux_battery_health())
            elif self.os_type == "darwin":
                health_info.update(self._get_macos_battery_health())
        except Exception as e:
            health_info["health_error"] = str(e)
        
        return health_info if health_info else None
    
    def _get_windows_battery_health(self) -> Dict[str, Any]:
        """Get Windows battery health using PowerShell and WMI"""
        health_info = {}
        
        try:
            powershell_cmd = """
            $battery = Get-WmiObject -Class Win32_Battery
            $report = powercfg /batteryreport /output temp_battery_report.html /duration 1
            Start-Sleep -Seconds 2
            
            if ($battery) {
                Write-Output "DesignCapacity:$($battery.DesignCapacity)"
                Write-Output "FullChargeCapacity:$($battery.FullChargeCapacity)"
                Write-Output "Chemistry:$($battery.Chemistry)"
                Write-Output "Status:$($battery.Status)"
            }
            
            if (Test-Path temp_battery_report.html) {
                $content = Get-Content temp_battery_report.html -Raw
                if ($content -match 'DESIGN CAPACITY.*?(\d+,?\d*)\s*mWh') {
                    $design = $matches[1] -replace ',', ''
                    Write-Output "ReportDesignCapacity:$design"
                }
                if ($content -match 'FULL CHARGE CAPACITY.*?(\d+,?\d*)\s*mWh') {
                    $full = $matches[1] -replace ',', ''
                    Write-Output "ReportFullCapacity:$full"
                }
                if ($content -match 'CYCLE COUNT.*?(\d+)') {
                    Write-Output "CycleCount:$matches[1]"
                }
                Remove-Item temp_battery_report.html -Force -ErrorAction SilentlyContinue
            }
            """
            
            result = subprocess.run(
                ['powershell', '-Command', powershell_cmd],
                capture_output=True, text=True, timeout=30, cwd=os.getcwd()
            )
            
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        if key == "DesignCapacity" and value.strip().isdigit():
                            health_info["design_capacity_mwh"] = int(value.strip())
                        elif key == "FullChargeCapacity" and value.strip().isdigit():
                            health_info["full_charge_capacity_mwh"] = int(value.strip())
                        elif key == "ReportDesignCapacity" and value.strip().isdigit():
                            health_info["design_capacity_mwh"] = int(value.strip())
                        elif key == "ReportFullCapacity" and value.strip().isdigit():
                            health_info["full_charge_capacity_mwh"] = int(value.strip())
                        elif key == "CycleCount" and value.strip().isdigit():
                            health_info["cycle_count"] = int(value.strip())
                        elif key == "Chemistry":
                            health_info["chemistry"] = value.strip()
                        elif key == "Status":
                            health_info["wmi_status"] = value.strip()
            
            if "design_capacity_mwh" in health_info and "full_charge_capacity_mwh" in health_info:
                design = health_info["design_capacity_mwh"]
                full = health_info["full_charge_capacity_mwh"]
                if design > 0:
                    health_percentage = (full / design) * 100
                    health_info["health_percentage"] = round(health_percentage, 1)
                    
                    if health_percentage >= 90:
                        health_info["health_status"] = "excellent"
                    elif health_percentage >= 80:
                        health_info["health_status"] = "good"
                    elif health_percentage >= 70:
                        health_info["health_status"] = "fair"
                    elif health_percentage >= 50:
                        health_info["health_status"] = "poor"
                    else:
                        health_info["health_status"] = "critical"
                        
        except Exception as e:
            health_info["windows_error"] = str(e)
        
        return health_info
    
    def _get_linux_battery_health(self) -> Dict[str, Any]:
        """Get Linux battery health from /sys/class/power_supply"""
        health_info = {}
        
        try:
            battery_paths = [
                "/sys/class/power_supply/BAT0",
                "/sys/class/power_supply/BAT1"
            ]
            
            for bat_path in battery_paths:
                if not os.path.exists(bat_path):
                    continue
                
                def read_battery_file(filename):
                    try:
                        with open(os.path.join(bat_path, filename), 'r') as f:
                            return f.read().strip()
                    except:
                        return None
                
                design_full = read_battery_file("energy_full_design")
                current_full = read_battery_file("energy_full")
                cycle_count = read_battery_file("cycle_count")
                technology = read_battery_file("technology")
                status = read_battery_file("status")
                
                if design_full and current_full:
                    try:
                        design_val = int(design_full)
                        current_val = int(current_full)
                        
                        health_info["design_capacity_uwh"] = design_val
                        health_info["full_charge_capacity_uwh"] = current_val
                        
                        if design_val > 0:
                            health_percentage = (current_val / design_val) * 100
                            health_info["health_percentage"] = round(health_percentage, 1)
                            
                            if health_percentage >= 90:
                                health_info["health_status"] = "excellent"
                            elif health_percentage >= 80:
                                health_info["health_status"] = "good"
                            elif health_percentage >= 70:
                                health_info["health_status"] = "fair"
                            elif health_percentage >= 50:
                                health_info["health_status"] = "poor"
                            else:
                                health_info["health_status"] = "critical"
                    except ValueError:
                        pass
                
                if cycle_count and cycle_count.isdigit():
                    health_info["cycle_count"] = int(cycle_count)
                
                if technology:
                    health_info["chemistry"] = technology
                
                if status:
                    health_info["battery_status"] = status
                
                break
                
        except Exception as e:
            health_info["linux_error"] = str(e)
        
        return health_info
    
    def _get_macos_battery_health(self) -> Dict[str, Any]:
        """Get macOS battery health using system_profiler and ioreg"""
        health_info = {}
        
        try:
            result = subprocess.run(
                ['system_profiler', 'SPPowerDataType', '-json'],
                capture_output=True, text=True, timeout=20
            )
            
            if result.stdout:
                import json
                power_data = json.loads(result.stdout)
                
                for item in power_data.get('SPPowerDataType', []):
                    if 'sppower_battery_health_info' in item:
                        battery_info = item['sppower_battery_health_info']
                        
                        if 'sppower_battery_cycle_count' in battery_info:
                            health_info["cycle_count"] = battery_info['sppower_battery_cycle_count']
                        
                        if 'sppower_battery_health' in battery_info:
                            health_status = battery_info['sppower_battery_health'].lower()
                            health_info["health_status"] = health_status
                        
                        if 'sppower_battery_max_capacity' in battery_info:
                            max_capacity = battery_info['sppower_battery_max_capacity']
                            if isinstance(max_capacity, str) and max_capacity.endswith('%'):
                                health_percentage = float(max_capacity.rstrip('%'))
                                health_info["health_percentage"] = health_percentage
            
            ioreg_result = subprocess.run(
                ['ioreg', '-r', '-c', 'AppleSmartBattery'],
                capture_output=True, text=True, timeout=15
            )
            
            if ioreg_result.stdout:
                for line in ioreg_result.stdout.split('\n'):
                    if '"DesignCapacity" =' in line:
                        try:
                            capacity = int(line.split('=')[1].strip())
                            health_info["design_capacity_mah"] = capacity
                        except:
                            pass
                    elif '"MaxCapacity" =' in line:
                        try:
                            capacity = int(line.split('=')[1].strip())
                            health_info["max_capacity_mah"] = capacity
                        except:
                            pass
                    elif '"BatteryData" =' in line and '"Chemistry"' in line:
                        if 'Lithium' in line:
                            health_info["chemistry"] = "Lithium-Ion"
            
            if "design_capacity_mah" in health_info and "max_capacity_mah" in health_info:
                design = health_info["design_capacity_mah"]
                max_cap = health_info["max_capacity_mah"]
                if design > 0:
                    health_percentage = (max_cap / design) * 100
                    health_info["health_percentage"] = round(health_percentage, 1)
                    
        except Exception as e:
            health_info["macos_error"] = str(e)
        
        return health_info
    
    def check_driver_updates(self) -> Dict[str, Any]:
        """Check for available driver updates (simplified)"""
        driver_info = {"available_updates": 0, "last_checked": "Unknown", "status": "unknown"}
        
        try:
            if self.os_type == "windows":
                result = subprocess.run(
                    ['powershell', '-Command', 'Get-WUList -MicrosoftUpdate | Measure-Object | Select-Object -ExpandProperty Count'],
                    capture_output=True, text=True, timeout=30
                )
                if result.stdout.strip().isdigit():
                    driver_info["available_updates"] = int(result.stdout.strip())
                    driver_info["status"] = "updates_available" if driver_info["available_updates"] > 0 else "up_to_date"
            
            elif self.os_type == "linux":
                result = subprocess.run(
                    ['apt', 'list', '--upgradable', '2>/dev/null', '|', 'grep', '-E', '(linux-|firmware-)'],
                    shell=True, capture_output=True, text=True, timeout=20
                )
                updates = len([line for line in result.stdout.split('\n') if line.strip()])
                driver_info["available_updates"] = max(0, updates - 1)
                driver_info["status"] = "updates_available" if driver_info["available_updates"] > 0 else "up_to_date"
                
        except Exception as e:
            driver_info["error"] = str(e)
        
        driver_info["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return driver_info
    
    def get_system_health_score(self, report: Dict) -> int:
        """Calculate overall system health score (0-100)"""
        score = 100
        
        storage = report.get("storage", {})
        if storage.get("percent_used", 0) > 90:
            score -= 20
        elif storage.get("percent_used", 0) > 80:
            score -= 10
        
        memory = report.get("memory", {})
        if memory.get("percent_used", 0) > 90:
            score -= 15
        elif memory.get("percent_used", 0) > 80:
            score -= 8
        
        battery = report.get("battery")
        if battery:
            if battery.get("percent", 100) < 20 and not battery.get("plugged"):
                score -= 10
            
            health_percentage = battery.get("health_percentage")
            if health_percentage:
                if health_percentage < 50:
                    score -= 25
                elif health_percentage < 70:
                    score -= 15
                elif health_percentage < 80:
                    score -= 8
            
            cycle_count = battery.get("cycle_count")
            if cycle_count:
                if cycle_count > 1000:
                    score -= 10
                elif cycle_count > 500:
                    score -= 5
        
        startup = report.get("startup", {})
        if startup.get("uptime_days", 0) > 30:
            score -= 5
        
        drivers = report.get("drivers", {})
        if drivers.get("available_updates", 0) > 5:
            score -= 15
        elif drivers.get("available_updates", 0) > 0:
            score -= 5
        
        return max(0, score)
    
    def collect_full_report(self) -> Dict[str, Any]:
        """Collect comprehensive system report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "storage": self.get_storage_info(),
            "memory": self.get_memory_info(),
            "startup": self.get_startup_info(),
            "autostart_programs": self.get_autostart_programs(),
            "services": self.get_running_services(),
            "battery": self.get_battery_info(),
            "drivers": self.check_driver_updates()
        }
        
        report["health_score"] = self.get_system_health_score(report)
        return report

class SmartGreeting:
    """Generate intelligent greetings and tips based on system report"""
    
    def __init__(self):
        self.console = Console()
    
    def generate_greeting(self, system_report: Dict) -> str:
        """Generate greeting based on system report"""
        health_score = system_report.get("health_score", 100)
        storage = system_report.get("storage", {})
        memory = system_report.get("memory", {})
        startup = system_report.get("startup", {})
        battery = system_report.get("battery")
        drivers = system_report.get("drivers", {})
        
        current_time = datetime.now()
        hour = current_time.hour
        
        if 5 <= hour < 12:
            time_greeting = "Good morning!"
        elif 12 <= hour < 17:
            time_greeting = "Good afternoon!"
        elif 17 <= hour < 21:
            time_greeting = "Good evening!"
        else:
            time_greeting = "Hello!"
        
        greeting_parts = [time_greeting]
        
        if health_score >= 95:
            greeting_parts.append("Your system is running exceptionally well today! Everything looks perfect.")
        elif health_score >= 85:
            greeting_parts.append("Your computer is performing great with excellent system health.")
        elif health_score >= 70:
            greeting_parts.append("Your system is running well, though there might be room for minor improvements.")
        elif health_score >= 50:
            greeting_parts.append("Your computer needs some attention to optimize performance.")
        else:
            greeting_parts.append("Your system requires immediate maintenance for better performance.")
        
        issues = []
        suggestions = []
        
        if storage.get("percent_used", 0) > 90:
            issues.append("critically low disk space")
            suggestions.append("free up disk space immediately")
        elif storage.get("percent_used", 0) > 80:
            issues.append("limited disk space")
            suggestions.append("consider cleaning up files")
        
        if memory.get("percent_used", 0) > 85:
            issues.append("high memory usage")
            suggestions.append("close unused applications")
        
        if startup.get("uptime_days", 0) > 14:
            issues.append(f"{startup.get('uptime_days')} days uptime")
            suggestions.append("restart your computer soon")
        
        if battery and battery.get("percent") < 20 and not battery.get("plugged"):
            issues.append("low battery")
            suggestions.append("connect your charger")
        
        if battery:
            health_percentage = battery.get("health_percentage")
            cycle_count = battery.get("cycle_count")
            
            if health_percentage and health_percentage < 70:
                health_status = battery.get("health_status", "unknown")
                issues.append(f"battery health at {health_percentage}% ({health_status})")
                if health_percentage < 50:
                    suggestions.append("consider battery replacement")
                else:
                    suggestions.append("monitor battery performance")
            
            if cycle_count and cycle_count > 800:
                issues.append(f"high battery cycles ({cycle_count})")
                suggestions.append("consider battery maintenance")
        
        if drivers.get("available_updates", 0) > 0:
            update_count = drivers.get("available_updates")
            issues.append(f"{update_count} driver updates available")
            suggestions.append("update your drivers")
        
        if issues:
            if len(issues) == 1:
                greeting_parts.append(f"I noticed {issues[0]}.")
            else:
                greeting_parts.append(f"I noticed a few things: {', '.join(issues[:-1])}, and {issues[-1]}.")
        
        if suggestions:
            if len(suggestions) == 1:
                greeting_parts.append(f"I'd recommend you {suggestions[0]}.")
            elif len(suggestions) == 2:
                greeting_parts.append(f"I'd recommend you {suggestions[0]} and {suggestions[1]}.")
            else:
                greeting_parts.append(f"I'd recommend you {', '.join(suggestions[:-1])}, and {suggestions[-1]}.")
        
        if health_score >= 85 and not issues:
            greeting_parts.append("Keep up the great work maintaining your system!")
        
        return " ".join(greeting_parts)
    
    def get_quick_tips(self, report: Dict) -> List[str]:
        """Generate helpful tips based on system state"""
        tips = []
        storage = report.get("storage", {})
        memory = report.get("memory", {})
        startup = report.get("startup", {})
        autostart = report.get("autostart_programs", [])
        battery = report.get("battery")
        
        if storage.get("percent_used", 0) > 80:
            tips.append("Run disk cleanup to free up space - empty trash, clear browser cache, and remove temporary files.")
        
        if memory.get("percent_used", 0) > 80:
            tips.append("Close unnecessary browser tabs and applications to free up RAM.")
        
        if startup.get("uptime_days", 0) > 7:
            tips.append("Restart your computer to apply updates and refresh system processes.")
        
        if len(autostart) > 10:
            tips.append("Review your startup programs - disable unnecessary ones to speed up boot time.")
        
        if battery:
            health_percentage = battery.get("health_percentage")
            cycle_count = battery.get("cycle_count")
            
            if health_percentage and health_percentage < 80:
                tips.append(f"Battery health is at {health_percentage}% - avoid extreme temperatures and deep discharges.")
            elif cycle_count and cycle_count > 500:
                tips.append("High battery cycle count - consider calibrating battery or reducing charge cycles.")
        
        if report.get("health_score", 100) < 80:
            tips.append("Run a system maintenance routine: update drivers, scan for malware, and clean temporary files.")
        
        return tips[:3]
    
    def _get_health_insights(self, report: Dict) -> List[str]:
        """Generate system health insights"""
        insights = []
        storage = report.get("storage", {})
        memory = report.get("memory", {})
        startup = report.get("startup", {})
        autostart = report.get("autostart_programs", [])
        
        if storage.get("percent_used", 0) < 50:
            insights.append("You have plenty of storage space available for new files and applications.")
        
        if memory.get("percent_used", 0) < 60:
            insights.append("Memory usage is optimal - your system should be running smoothly.")
        
        if startup.get("uptime_days", 0) < 1:
            insights.append("Recent restart detected - your system should be running fresh and fast.")
        
        uptime_hours = startup.get("uptime_hours", 0)
        if 24 <= uptime_hours <= 168:
            insights.append("Your uptime is in a good range - not too fresh, not too stale.")
        
        if len(autostart) < 5:
            insights.append("You have a clean startup configuration with minimal autostart programs.")
        
        return insights

class ConfigManager:
    """Handle configuration file management"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.default_config = {
            "display_sections": {
                "storage": True,
                "memory": True,
                "startup": True,
                "battery": True,
                "autostart": True,
                "services": False,
                "drivers": True
            },
            "greeting_style": "friendly",
            "show_tips": True,
            "show_insights": True,
            "health_warnings": True,
            "max_autostart_display": 5,
            "max_services_display": 5,
            "personality_greetings": True
        }
    
    def load_config(self) -> Dict:
        """Load configuration from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                return {**self.default_config, **config}
            except:
                pass
        
        self.save_config(self.default_config)
        return self.default_config
    
    def save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

class SystemGreeter:
    """Main application class"""
    
    def __init__(self):
        self.console = Console()
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.monitor = SystemMonitor()
        self.greeter = SmartGreeting()
    
    def display_system_report(self, report: Dict):
        """Display formatted system report using Rich"""
        layout = Layout()
        
        header = Panel(
            f"[bold blue]System Report[/bold blue] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            box=box.ROUNDED
        )
        
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        table.add_column("Component", style="cyan", width=15)
        table.add_column("Status", style="green", width=50)
        table.add_column("Health", justify="center", width=10)
        
        sections = self.config["display_sections"]
        
        if sections.get("storage"):
            storage = report.get("storage", {})
            status = f"{storage.get('used_gb', 0):.1f}GB / {storage.get('total_gb', 0):.1f}GB ({storage.get('percent_used', 0)}%)"
            health = "⚠️" if storage.get("status") == "low" else "✅"
            table.add_row("Storage", status, health)
        
        if sections.get("memory"):
            memory = report.get("memory", {})
            status = f"{memory.get('used_gb', 0):.1f}GB / {memory.get('total_gb', 0):.1f}GB ({memory.get('percent_used', 0)}%)"
            health = "⚠️" if memory.get("status") == "high" else "✅"
            table.add_row("Memory", status, health)
        
        if sections.get("startup"):
            startup = report.get("startup", {})
            status = f"Up {startup.get('uptime_days', 0)} days, {startup.get('uptime_hours', 0):.1f} hours"
            health = "⚠️" if startup.get("status") == "long" else "✅"
            table.add_row("Uptime", status, health)
        
        if sections.get("battery") and report.get("battery"):
            battery = report["battery"]
            status_parts = [f"{battery['percent']}% ({'Charging' if battery['plugged'] else 'On Battery'})"]
            
            health_percentage = battery.get("health_percentage")
            if health_percentage:
                health_status = battery.get("health_status", "unknown")
                status_parts.append(f"Health: {health_percentage}% ({health_status})")
            
            cycle_count = battery.get("cycle_count")
            if cycle_count:
                status_parts.append(f"Cycles: {cycle_count}")
            
            status = " | ".join(status_parts)
            health = "⚠️" if (battery.get("status") == "critical" or 
                            (health_percentage and health_percentage < 80) or 
                            (cycle_count and cycle_count > 800)) else "✅"
            table.add_row("Battery", status, health)
        
        if sections.get("drivers"):
            drivers = report.get("drivers", {})
            updates = drivers.get("available_updates", 0)
            status = f"{updates} updates available" if updates > 0 else "Up to date"
            health = "⚠️" if updates > 0 else "✅"
            table.add_row("Drivers", status, health)
        
        health_score = report.get("health_score", 100)
        score_color = "green" if health_score >= 90 else "yellow" if health_score >= 70 else "red"
        table.add_row("Overall Health", f"[{score_color}]{health_score}/100[/{score_color}]", "🎯")
        
        self.console.print(header)
        self.console.print(table)
        
        if sections.get("autostart"):
            autostart = report.get("autostart_programs", [])
            if autostart and len(autostart) > 0:
                self.console.print(f"\n[bold]Autostart Programs ({len(autostart)}):[/bold]")
                display_count = min(len(autostart), self.config["max_autostart_display"])
                for i, program in enumerate(autostart[:display_count]):
                    self.console.print(f"  {i+1}. {program}")
                if len(autostart) > display_count:
                    self.console.print(f"  ... and {len(autostart) - display_count} more")
    
    def run(self, show_report: bool = True, show_greeting: bool = True):
        """Main execution function"""
        try:
            with self.console.status("[bold green]Analyzing your system..."):
                report = self.monitor.collect_full_report()
            
            if show_report:
                self.display_system_report(report)
                self.console.print()
            
            if show_greeting:
                greeting = self.greeter.generate_greeting(report)
                
                greeting_panel = Panel(
                    greeting,
                    title="[bold green]🖥️ System Assistant[/bold green]",
                    title_align="left",
                    border_style="green",
                    box=box.ROUNDED
                )
                self.console.print(greeting_panel)
                
                if self.config.get("show_tips", True):
                    tips = self.greeter.get_quick_tips(report)
                    if tips:
                        self.console.print("\n[bold]💡 Quick Tips:[/bold]")
                        for tip in tips:
                            self.console.print(f"  {tip}")
                
                if self.config.get("show_insights", True):
                    insights = self.greeter._get_health_insights(report)
                    if len(insights) > 1:
                        self.console.print(f"\n[bold]📊 System Insights:[/bold]")
                        for insight in insights[1:3]:
                            self.console.print(f"  • {insight}")
            
            self.console.print("\n[dim]Press Enter to exit...[/dim]")
            input()
            
            return report
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted by user[/yellow]")
            return None
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return None

def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart System Monitor & Greeting")
    parser.add_argument("--no-report", action="store_true", help="Skip system report display")
    parser.add_argument("--no-greeting", action="store_true", help="Skip smart greeting")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--save-report", help="Save report to JSON file")
    
    args = parser.parse_args()
    
    greeter = SystemGreeter()
    greeter.config_manager.config_path = Path(args.config)
    greeter.config = greeter.config_manager.load_config()
    
    report = greeter.run(
        show_report=not args.no_report,
        show_greeting=not args.no_greeting
    )
    
    if args.save_report and report:
        try:
            with open(args.save_report, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\nReport saved to {args.save_report}")
        except Exception as e:
            print(f"Error saving report: {e}")

if __name__ == "__main__":
    main()