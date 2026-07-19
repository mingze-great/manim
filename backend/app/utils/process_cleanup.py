import os
import time
import signal
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not installed, process cleanup features will be limited")


def cleanup_zombie_processes() -> List[int]:
    """清理僵尸进程"""
    if not HAS_PSUTIL:
        return []
    
    zombies = []
    for proc in psutil.process_iter(['pid', 'name', 'status']):
        try:
            if proc.info['status'] == psutil.STATUS_ZOMBIE:
                zombies.append(proc.info['pid'])
                try:
                    os.waitpid(proc.info['pid'], os.WNOHANG)
                    logger.info(f"Cleaned zombie process: {proc.info['pid']}")
                except Exception as e:
                    logger.debug(f"Failed to clean zombie {proc.info['pid']}: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return zombies


def kill_orphaned_manim_processes(max_age_seconds: int = 7200) -> List[Dict]:
    """杀死孤儿 manim 进程（运行超过指定时间）
    
    Args:
        max_age_seconds: 最大运行时间（秒），默认2小时
    
    Returns:
        被杀死的进程列表
    """
    if not HAS_PSUTIL:
        return []
    
    killed = []
    current_time = time.time()
    
    for proc in psutil.process_iter(['pid', 'name', 'create_time', 'cmdline', 'ppid']):
        try:
            cmdline = proc.info['cmdline'] or []
            cmdline_str = ' '.join(cmdline).lower()
            
            # 检查是否是 manim 相关进程
            is_manim = any([
                'manim' in cmdline_str,
                'scene.py' in cmdline_str,
                '-m manim' in cmdline_str,
            ])
            
            if is_manim:
                age = current_time - proc.info['create_time']
                
                # 检查父进程
                try:
                    parent = proc.parent()
                    is_orphan = parent is None or parent.pid == 1
                except:
                    is_orphan = True
                
                # 如果是孤儿进程且运行时间超过阈值
                if is_orphan and age > max_age_seconds:
                    proc_info = {
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'age_seconds': int(age),
                        'cmdline': cmdline_str[:100]
                    }
                    
                    try:
                        proc.kill()
                        killed.append(proc_info)
                        logger.info(f"Killed orphan manim process: PID={proc.info['pid']}, Age={int(age)}s")
                    except Exception as e:
                        logger.warning(f"Failed to kill process {proc.info['pid']}: {e}")
                        
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return killed


def kill_stale_python_processes(max_age_seconds: int = 10800) -> List[Dict]:
    """杀死长时间运行的 Python 子进程（超过3小时）
    
    注意：只杀死 uvicorn 主进程的子进程
    """
    if not HAS_PSUTIL:
        return []
    
    killed = []
    current_time = time.time()
    
    # 获取 uvicorn 主进程
    uvicorn_pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline'] or []
            if 'uvicorn' in ' '.join(cmdline):
                uvicorn_pids.append(proc.info['pid'])
        except:
            pass
    
    if not uvicorn_pids:
        return []
    
    # 检查子进程
    for uvicorn_pid in uvicorn_pids:
        try:
            parent = psutil.Process(uvicorn_pid)
            children = parent.children(recursive=True)
            
            for child in children:
                try:
                    age = current_time - child.create_time()
                    if age > max_age_seconds:
                        proc_info = {
                            'pid': child.pid,
                            'name': child.name(),
                            'age_seconds': int(age),
                            'ppid': uvicorn_pid
                        }
                        child.kill()
                        killed.append(proc_info)
                        logger.info(f"Killed stale child process: PID={child.pid}, Age={int(age)}s")
                except:
                    pass
        except:
            pass
    
    return killed


def get_process_stats() -> Dict:
    """获取进程统计信息"""
    if not HAS_PSUTIL:
        return {'error': 'psutil not installed'}
    
    stats = {
        'total_processes': len(psutil.pids()),
        'manim_processes': 0,
        'python_processes': 0,
        'zombie_processes': 0,
        'top_cpu_processes': [],
        'top_memory_processes': []
    }
    
    processes_info = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline', 'status']):
        try:
            info = proc.info
            processes_info.append(info)
            
            cmdline = ' '.join(info['cmdline'] or []).lower()
            if 'manim' in cmdline or 'scene.py' in cmdline:
                stats['manim_processes'] += 1
            
            if 'python' in info['name'].lower():
                stats['python_processes'] += 1
            
            if info['status'] == psutil.STATUS_ZOMBIE:
                stats['zombie_processes'] += 1
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # CPU 占用最高的进程
    processes_info.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
    stats['top_cpu_processes'] = [
        {'pid': p['pid'], 'name': p['name'], 'cpu': p['cpu_percent']}
        for p in processes_info[:5]
    ]
    
    # 内存占用最高的进程
    processes_info.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
    stats['top_memory_processes'] = [
        {'pid': p['pid'], 'name': p['name'], 'memory': p['memory_percent']}
        for p in processes_info[:5]
    ]
    
    return stats


def cleanup_all(max_process_age: int = 7200) -> Dict:
    """执行所有清理任务
    
    Args:
        max_process_age: 进程最大年龄（秒）
    
    Returns:
        清理结果
    """
    results = {
        'zombies_cleaned': cleanup_zombie_processes(),
        'orphan_processes_killed': kill_orphaned_manim_processes(max_process_age),
        'stale_processes_killed': kill_stale_python_processes(max_process_age + 3600),
        'process_stats': get_process_stats()
    }
    
    return results