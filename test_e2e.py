#!/usr/bin/env python3
import requests
import time
import json

BASE_URL = "http://106.52.166.109:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

def print_step(step_name):
    print("\n" + "=" * 60)
    print(f"📌 {step_name}")
    print("=" * 60)

def main():
    # Step 1: 登录
    print_step("1. 登录获取 Token")
    login_data = {"username": ADMIN_USER, "password": ADMIN_PASS}
    resp = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
    print(f"响应状态码: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ 登录失败: {resp.text}")
        return False

    token_info = resp.json()
    access_token = token_info["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    print(f"✅ 登录成功")
    print(f"Token: {access_token[:50]}...")

    # Step 2: 获取项目列表
    print_step("2. 获取项目列表")
    resp = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    print(f"响应状态码: {resp.status_code}")
    if resp.status_code == 200:
        projects = resp.json()
        print(f"✅ 找到 {len(projects)} 个项目")
        for p in projects:
            print(f"  - ID: {p['id']}, 标题: {p['title']}, 状态: {p['status']}")
    else:
        print(f"❌ 获取项目列表失败: {resp.text}")
        return False

    # Step 3: 创建新项目
    print_step("3. 创建新项目（模板6测试）")
    project_data = {
        "title": "模板6端到端测试",
        "description": "测试模板6完整流程：对话→代码生成→渲染",
        "template_id": 6
    }
    resp = requests.post(f"{BASE_URL}/api/projects", headers=headers, json=project_data)
    print(f"响应状态码: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ 创建项目失败: {resp.text}")
        return False

    project = resp.json()
    project_id = project["id"]
    print(f"✅ 项目创建成功")
    print(f"  - 项目ID: {project_id}")
    print(f"  - 项目标题: {project['title']}")

    # Step 4: 发送对话消息（进入聊天模式）
    print_step("4. 发送对话消息")
    message = "我想创建一个关于十大思维模型的视频，包括：第一性原理、逆向思维、系统思维、批判性思维、设计思维、侧向思维、归纳演绎、类比思维、发散思维、收敛思维"
    chat_data = {
        "message": message,
        "theme": "十大思维模型"
    }
    resp = requests.post(f"{BASE_URL}/api/projects/{project_id}/chat", headers=headers, json=chat_data)
    print(f"响应状态码: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ 发送消息失败: {resp.text}")
        return False

    chat_result = resp.json()
    print(f"✅ 消息发送成功")
    print(f"  - 消息内容: {message}")

    # Step 5: 模拟"满意"操作（需要发送流式消息）
    print_step("5. 发送\"满意\"确认消息")
    satisfied_data = {
        "message": "满意",
        "theme": "十大思维模型"
    }
    resp = requests.post(f"{BASE_URL}/api/projects/{project_id}/chat", headers=headers, json=satisfied_data)
    print(f"响应状态码: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ 发送满意消息失败: {resp.text}")
        return False

    print(f"✅ 满意消息已发送")

    # Step 6: 查询项目状态（等待代码生成完成）
    print_step("6. 等待代码生成完成")
    max_wait = 180  # 最多等待3分钟
    wait_interval = 5
    elapsed = 0

    while elapsed < max_wait:
        resp = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
        if resp.status_code == 200:
            project = resp.json()
            print(f"  项目状态: {project['status']}, 进度: {project.get('progress', 'N/A')}")

            if project['status'] == 'code_generated' and project['manim_code']:
                print(f"✅ 代码生成完成")
                print(f"  - 代码长度: {len(project['manim_code'])} 字符")
                break
            elif project['status'] == 'failed':
                print(f"❌ 项目失败: {project.get('error_message', 'Unknown error')}")
                return False
        else:
            print(f"❌ 查询项目状态失败: {resp.text}")
            return False

        time.sleep(wait_interval)
        elapsed += wait_interval
        print(f"  等待中... ({elapsed}/{max_wait}秒)")

    if elapsed >= max_wait:
        print(f"❌ 等待超时")
        return False

    # Step 7: 触发渲染
    print_step("7. 触发视频渲染")
    render_data = {
        "template_id": 6
    }
    resp = requests.post(f"{BASE_URL}/api/tasks/generate", headers=headers, json=render_data)
    print(f"响应状态码: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ 触发渲染失败: {resp.text}")
        return False

    task = resp.json()
    task_id = task["id"]
    print(f"✅ 渲染任务已创建")
    print(f"  - 任务ID: {task_id}")

    # Step 8: 监控渲染进度
    print_step("8. 监控渲染进度")
    elapsed = 0
    max_wait = 600  # 最多等待10分钟

    while elapsed < max_wait:
        resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
        if resp.status_code == 200:
            task = resp.json()
            print(f"  任务状态: {task['status']}, 进度: {task['progress']}%")

            if task['status'] == 'completed':
                video_url = task.get('video_url')
                print(f"✅ 渲染完成")
                print(f"  - 视频URL: {video_url}")
                if video_url:
                    full_video_url = f"{BASE_URL}{video_url}"
                    print(f"  - 完整视频URL: {full_video_url}")
                break
            elif task['status'] == 'failed':
                error_msg = task.get('error_message', 'Unknown error')
                print(f"❌ 渲染失败: {error_msg}")
                if task.get('log'):
                    print(f"  - 错误日志:\n{task['log']}")
                return False
        else:
            print(f"❌ 查询任务状态失败: {resp.text}")
            return False

        time.sleep(wait_interval)
        elapsed += wait_interval
        print(f"  等待中... ({elapsed}/{max_wait}秒)")

    if elapsed >= max_wait:
        print(f"❌ 渲染超时")
        return False

    # Summary
    print_step("✅ 测试完成")
    print(f"所有步骤执行成功！")
    print(f"项目ID: {project_id}")
    print(f"任务ID: {task_id}")
    print(f"视频URL: {full_video_url}")

    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
