import psutil
import shutil
import platform
from datetime import datetime
import wmi

class PerformanceMonitor:
    @staticmethod
    def get_cpu_percent() -> float:
        """获取CPU使用率"""
        return psutil.cpu_percent() / 100.0
    
    @staticmethod
    def get_memory_percent() -> float:
        """获取内存使用率"""
        memory = psutil.virtual_memory()
        return memory.percent / 100.0
    
    @staticmethod
    def get_disk_percent(path:str="/") -> tuple[float, int]:
        """获取磁盘使用率百分比"""
        try:
            if platform.system() == "Windows":
                path = "C:\\"
            
            usage = shutil.disk_usage(path)
            percent = usage.used / usage.total
            return percent, usage.free // (1024**3)  # 返回百分比和剩余GB数
        except Exception as e:
            return None, f"错误: {str(e)}"
        
        
    @staticmethod
    def get_battery_percent() -> float:
        """获取电池电量"""
        if platform.system() == "Windows":
            try:
                battery = psutil.sensors_battery()
                if battery:
                    return battery.percent / 100.0
                else:
                    return 1.0 
            except:
                return 1.0
        else:
            return 1.0
    
    @staticmethod
    def get_day_progress() -> float:
        """获取日进度"""
        now = datetime.now()
        return (now.hour * 3600 + now.minute * 60 + now.second) / (24 * 3600)
    
    @staticmethod
    def get_week_progress() -> float:
        """获取周进度"""
        now = datetime.now()
        week_day = now.weekday()  # 周一为0，周日为6
        return (week_day + 1) / 7
    
    @staticmethod
    def get_month_progress() -> float:
        """获取月进度"""
        now = datetime.now()
        days_in_month = 31  # 简化处理，实际月份天数不同
        if now.month in [4, 6, 9, 11]:
            days_in_month = 30
        elif now.month == 2:
            if now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0):
                days_in_month = 29
            else:
                days_in_month = 28
        return now.day / days_in_month
    
    @staticmethod
    def get_year_progress():
        """获取年进度"""
        now = datetime.now()
        days_in_year = 366 if now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0) else 365
        day_of_year = now.timetuple().tm_yday
        return (day_of_year - 1 + (now.hour * 3600 + now.minute * 60 + now.second) / (24 * 3600)) / days_in_year