import requests
import os
from datetime import datetime
import html  # 用于转义 HTML 特殊字符，防止报错

# 1. 获取 GitHub Secrets
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHAT_ID = os.environ.get("TG_CHAT_ID")

def get_epic_free_games():
    # 直接请求英文数据，速度最快，图片最全
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US"
    try:
        res = requests.get(url).json()
        games = res['data']['Catalog']['searchStore']['elements']
        
        free_games = []
        for game in games:
            # 1. 基础过滤：必须有促销信息
            promotions = game.get('promotions')
            if not promotions:
                continue
            
            if not promotions.get('promotionalOffers'):
                continue
            
            # 【重要】注释掉类型过滤，确保能抓到霍格沃茨之遗等大作
            # offer_type = game.get('offerType')
            # if offer_type and offer_type != 'BASE_GAME':
            #     continue

            # 2. 检查价格是否为 0
            offers = promotions['promotionalOffers']
            if not offers:
                continue

            is_free = False
            end_date_str = "未知"

            for offer_group in offers:
                for offer in offer_group['promotionalOffers']:
                    if offer['discountSetting']['discountPercentage'] == 0:
                        is_free = True
                        raw_date = offer.get('endDate')
                        if raw_date:
                            try:
                                # 格式化时间
                                dt = datetime.strptime(raw_date.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                end_date_str = dt.strftime("%Y-%m-%d %H:%M") + " (UTC)"
                            except:
                                end_date_str = raw_date
                        break
            
            if is_free:
                title = game.get('title')
                description = game.get('description', '暂无描述')
                slug = game.get('productSlug') or game.get('urlSlug')
                link = f"https://store.epicgames.com/p/{slug}" if slug else "https://store.epicgames.com/free-games"
                
                # 获取封面图
                image_url = ""
                for img in game.get('keyImages', []):
                    if img.get('type') == 'Thumbnail':
                        image_url = img.get('url')
                        break
                    elif img.get('type') == 'OfferImageWide':
                        image_url = img.get('url')

                free_games.append({
                    "title": title,
                    "description": description,
                    "link": link,
                    "image": image_url,
                    "end_date": end_date_str
                })
                
        return free_games
        
    except Exception as e:
        print(f"获取 Epic 数据出错: {e}")
        return []

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ 错误：未设置 Token 或 Chat ID")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",  # 使用 HTML 模式，稳定且支持格式
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ 推送错误: {e}")

if __name__ == "__main__":
    print("⏳ 开始检查 Epic 免费游戏...")
    games = get_epic_free_games()
    
    if games:
        print(f"🎉 发现 {len(games)} 个免费游戏")
        for g in games:
            # 简单转义，防止标题里有 & < > 等符号导致发送失败
            safe_title = html.escape(g['title'])
            safe_desc = html.escape(g['description'])
            
            msg = (
                f"<a href='{g['image']}'>&#8205;</a>"
                f"🔥 <b>Epic 喜加一提醒</b> 🔥\n\n"
                f"🎮 <b>{safe_title}</b>\n"
                f"⏰ 截止: {g['end_date']}\n\n"
                f"📝 {safe_desc}\n\n"
                f"🔗 <a href='{g['link']}'>点击领取游戏</a>"
            )
            send_telegram_message(msg)
            print(f"已推送: {safe_title}")
    else:
        print("🤷‍♂️ 当前没有检测到免费游戏")
