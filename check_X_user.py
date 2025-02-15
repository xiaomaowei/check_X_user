import json
import asyncio
import random
import csv
import os
from datetime import datetime, timezone, timedelta
from twikit import Client
from prettytable import PrettyTable  # 用于终端表格输出
from tqdm import tqdm  # 进度条

COOKIES_FILE = "cookies.json"
USER_LIST_FILE = "x_user_list.txt"
OUTPUT_CSV = "twitter_user_status.csv"

async def get_user_status(client, username):
    """获取用户状态（正常、冻结、停用、封禁）、昵称、是否为机器人、封禁原因、关注者数、发文数及最新推文时间"""
    try:
        # 获取用户对象
        user_info = await client.get_user_by_screen_name(username)

        # 用户不存在
        if not user_info:
            return username, "N/A", "用户不存在", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"

        # 获取用户 ID & 昵称
        user_id = user_info.id
        name = user_info.name  # 获取昵称

        # 获取用户状态
        if getattr(user_info, "protected", False):
            status = "受保护 (Protected)"
            ban_reason = "仅限关注者查看"
        elif getattr(user_info, "verified", False):
            status = "已认证用户 (Verified)"
            ban_reason = "无"
        else:
            status = "正常 (Active)"
            ban_reason = "无"

        # 检测是否为机器人
        is_bot = "是 (Yes)" if getattr(user_info, "is_translator", False) else "否 (No)"

        # 获取关注者数量 & 发文数量
        followers_count = user_info.followers_count
        statuses_count = user_info.statuses_count

        # 获取最新推文
        tweets = await client.get_user_tweets(user_id, tweet_type="Tweets", count=1)

        # 处理推文时间 (UTC+8)
        if tweets:
            tweet_time_utc = datetime.strptime(tweets[0].created_at, "%a %b %d %H:%M:%S +0000 %Y")
            tweet_time_local = tweet_time_utc.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))
            latest_tweet_time = tweet_time_local.strftime("%Y-%m-%d %H:%M:%S UTC+8")
        else:
            latest_tweet_time = "无推文"

        return username, name, status, is_bot, followers_count, statuses_count, ban_reason, latest_tweet_time

    except Exception as e:
        error_message = str(e)
        if "403" in error_message:
            return username, "N/A", "账号受限或封禁 (Restricted / Banned)", "N/A", "N/A", "N/A", "可能违反政策", "N/A"
        elif "404" in error_message:
            return username, "N/A", "用户不存在 (Not Found)", "N/A", "N/A", "N/A", "用户删除或从未注册", "N/A"
        else:
            return username, "N/A", "无法获取", "N/A", "N/A", "N/A", error_message, "N/A"

async def login():
    """使用 cookies 登录 Twitter"""
    client = Client("en-US")

    # 读取并设置 cookies
    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    client.set_cookies({cookie["name"]: cookie["value"] for cookie in cookies})

    print("✅ 成功加载 cookies，登录 Twitter")
    return client

async def main():
    """主逻辑：登录 -> 读取用户列表 -> 获取状态 -> 输出表格 -> 统计用户数 -> 保存 CSV"""
    if not os.path.exists(COOKIES_FILE):
        print(f"❌ Cookie 文件未找到: {COOKIES_FILE}，请先手动登录 Twitter 并导出 cookies.json")
        return

    # 登录 Twitter
    client = await login()

    # 读取用户列表
    if not os.path.exists(USER_LIST_FILE):
        print(f"❌ 用户列表文件未找到: {USER_LIST_FILE}")
        return

    with open(USER_LIST_FILE, "r", encoding="utf-8") as f:
        users = [line.strip() for line in f if line.strip()]

    results = []
    table = PrettyTable(["用户名", "昵称", "状态", "是否机器人", "关注者数", "发文数", "封禁原因", "最新推文 (UTC+8)"])
    table.align = "l"

    # 进度条
    for user in tqdm(users, desc="查询用户状态", unit="个"):
        result = await get_user_status(client, user)
        results.append(result)
        table.add_row(result)

        # 随机延迟 1~3 秒，防止封号
        await asyncio.sleep(random.uniform(1, 3))

    # 输出表格到终端
    print(table)

    # 统计用户数量
    print(f"\n📊 总共有：{len(users)} 个账号已绑定\n")

    # 保存到 CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["用户名", "昵称", "状态", "是否机器人", "关注者数", "发文数", "封禁原因", "最新推文 (UTC+8)"])
        writer.writerows(results)

    print(f"🎉 数据已保存至 {OUTPUT_CSV}")

if __name__ == "__main__":
    asyncio.run(main())