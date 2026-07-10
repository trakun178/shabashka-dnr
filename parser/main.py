        for update in results:
            print(f"\n Обрабатываем обновление...")
            print(f"🔍 Keys в update: {update.keys()}")
            print(f" Весь update: {update}")
            
            if 'channel_post' in update:
                post = update['channel_post']
                message_id = post['message_id']
                
                print(f"  📨 Message ID: {message_id}")
                print(f"  🔍 Keys в post: {post.keys()}")
                
                # Получаем текст
                text = post.get('text', '')
                
                # Если текста нет, пробуем взять caption
                if not text:
                    if 'caption' in post:
                        text = post['caption']
                        print(f"  📝 Взято из caption (длина: {len(text)})")
                    else:
                        print(f"  ⚠️ Нет текста или caption")
                        skipped_no_text += 1
                        if message_id > max_id:
                            max_id = message_id
                        continue
                
                print(f"  📝 Текст (первые 50 символов): {text[:50]}...")
                
                if message_id > last_id and text:
                    ad = {
                        'tg_message_id': message_id,
                        'title': text[:100] if len(text) > 100 else text,
                        'description': text,
                        'category': parse_category(text),
                        'city': parse_city(text),
                        'phone': extract_phone(text),
                        'photo_url': None,
                        'created_at': datetime.now().isoformat()
                    }
                    
                    new_ads.append(ad)
                    max_id = message_id
                    print(f"  ✅ Добавлено объявление #{message_id}")
            else:
                print(f"  ⚠️ Нет 'channel_post' в update!")