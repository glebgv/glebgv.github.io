#!/usr/bin/env python3
"""
Telegram notifier для Hugo сайта на GitHub Pages
Автоматически публикует новые статьи в Telegram канал с rate limit handling
"""

import os
import glob
import json
import time
import requests
from datetime import datetime
from pathlib import Path
import frontmatter

# Конфигурация из GitHub Secrets
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
SITE_URL = os.environ.get('SITE_URL', 'https://your-site.github.io')
STATE_FILE = '.github/published_posts.json'
MAX_POSTS_PER_RUN = int(os.environ.get('MAX_POSTS_PER_RUN', '10'))
DELAY_BETWEEN_POSTS = float(os.environ.get('DELAY_BETWEEN_POSTS', '2.0'))


def load_published_posts():
    """Загружает список уже опубликованных статей"""
    if Path(STATE_FILE).exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ Ошибка чтения {STATE_FILE}: {e}")
            return []
    return []


def save_published_posts(posts):
    """Сохраняет список опубликованных статей"""
    Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
        print(f"💾 Состояние сохранено: {len(posts)} постов")
    except IOError as e:
        print(f"❌ Ошибка сохранения {STATE_FILE}: {e}")


def get_new_posts():
    """Находит новые статьи в content/ (не опубликованные ранее)"""
    published = set(load_published_posts())
    new_posts = []
    
    # Сканируем все markdown файлы рекурсивно
    md_files = glob.glob('content/**/*.md', recursive=True)
    print(f"🔍 Сканируем {len(md_files)} файлов...")
    
    for md_file in md_files:
        # Пропускаем уже опубликованные
        if md_file in published:
            continue
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                
                # Пропускаем черновики
                if post.get('draft', False):
                    continue
                
                # Пропускаем статьи с будущей датой
                post_date = post.get('date')
                if post_date and isinstance(post_date, str):
                    try:
                        post_date = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                    except:
                        post_date = datetime.now()
                elif hasattr(post_date, 'isoformat'):
                    post_date = post_date.isoformat()
                else:
                    post_date = datetime.now()
                
                if post_date > datetime.now():
                    print(f"⏳ Будущая дата: {md_file}")
                    continue
                
                new_posts.append({
                    'file': md_file,
                    'title': post.get('title', 'Без названия'),
                    'date': post_date.isoformat(),
                    'description': post.get('description', '')[:200] + '...' if len(post.get('description', '')) > 200 else post.get('description', ''),
                    'tags': post.get('tags', [])
                })
                
        except Exception as e:
            print(f"⚠️ Ошибка при парсинге {md_file}: {e}")
    
    return new_posts[:MAX_POSTS_PER_RUN]  # Лимит за один запуск


def get_post_url(file_path):
    """Формирует URL статьи из пути к файлу"""
    # Убираем content/, index и .md
    path = Path(file_path)
    slug = path.parent.name if path.stem == 'index' else path.stem
    url_path = str(path.parent / slug).replace('content/', '').rstrip('/')
    return f"{SITE_URL}/{url_path}".rstrip('/')


def send_to_telegram(post):
    """
    Отправляет пост в Telegram канал с retry и rate limit handling
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Форматируем красивое сообщение
    message = f"📝 <b>{post['title']}</b>\n\n"
    
    if post['description']:
        message += f"{post['description']}\n\n"
    
    if post['tags']:
        tags = ' '.join([f"#{tag.replace(' ', '_').replace('/', '_')}" for tag in post['tags'][:5]])
        message += f"{tags}\n\n"
    
    post_url = get_post_url(post['file'])
    message += f"🔗 <a href='{post_url}'>Читать статью</a>"
    
    payload = {
        'chat_id': CHANNEL_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }
    
    # Retry с обработкой rate limit
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=15)
            data = response.json()
            
            if response.status_code == 200:
                print(f"✅ Опубликовано: {post['title'][:50]}...")
                return True
            
            elif response.status_code == 429:  # Rate limit
                retry_after = data.get('parameters', {}).get('retry_after', 1)
                print(f"⏳ Rate limit, ждём {retry_after}s (попытка {attempt+1})")
                time.sleep(retry_after + 0.5)
                continue
            
            else:
                print(f"❌ Ошибка {response.status_code}: {data}")
                break
                
        except requests.RequestException as e:
            print(f"❌ Network error (попытка {attempt+1}): {e}")
            time.sleep(1)
    
    print(f"❌ Не удалось опубликовать: {post['title'][:50]}...")
    return False


def main():
    """Основная функция"""
    print(f"🚀 Telegram Notifier запущен: {datetime.now().isoformat()}")
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Критическая ошибка: не установлены TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID")
        return 1
    
    new_posts = get_new_posts()
    
    if not new_posts:
        print("ℹ️ Новых статей не найдено")
        return 0
    
    print(f"📊 Найдено новых статей: {len(new_posts)}")
    
    published = load_published_posts()
    success_count = 0
    
    for i, post in enumerate(new_posts):
        print(f"\n--- Пост {i+1}/{len(new_posts)}: {post['title'][:50]}...")
        
        if send_to_telegram(post):
            published.append(post['file'])
            success_count += 1
        
        # Задержка между постами (КРИТИЧЕСКИ ВАЖНО!)
        if i < len(new_posts) - 1:
            print(f"⏳ Задержка {DELAY_BETWEEN_POSTS}s перед следующим постом...")
            time.sleep(DELAY_BETWEEN_POSTS)
    
    # Сохраняем состояние
    save_published_posts(published)
    
    print(f"\n🎉 ИТОГО: успешно {success_count}/{len(new_posts)}")
    return 0 if success_count == len(new_posts) else 1


if __name__ == '__main__':
    exit(main())
