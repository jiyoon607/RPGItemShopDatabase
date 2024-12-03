from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
from django.db import connection

from .models import *

# Create your views here.
def mainpage(request):
    player_id = request.session.get('player_id')
    player = None
    shops = Shop.objects.all()
    shop_1 = Shop.objects.get(id=1)
    shop_item_managements = Shopitemmanagement.objects.filter(shop=shop_1)
    transactionhistories = Transactionhistory.objects.all().order_by('-date')[:7]
    data = {}  # 초기 data를 빈 딕셔너리로 설정
    inventory_sell_data = []
    shop_infos = []

    # 날짜를 4일 감소시킨 후 메모리 상에서 정렬
    transactionhistories = sorted(
        [history for history in transactionhistories],
        key=lambda x: x.date - timedelta(days=4),
        reverse=True
    )[:7]

    # 날짜를 4일 감소시키기 (1회용)
    for history in transactionhistories:
        history.date -= timedelta(days=4)
        
    # shop_infos 구성
    for shop in shops:
        shop_item_managements = Shopitemmanagement.objects.filter(shop=shop)
        shop_infos.append({
            'shop': shop,
            'shop_item_managements': list(shop_item_managements)
        })

    if player_id:
        inventory_items = Inventoryitem.objects.filter(inventory_player=player_id).select_related('item')
        player = Player.objects.get(id=player_id)
        data['player'] = player  # player 추가
        data.update({
            'inventory_items': inventory_items
        })

        # inventory_sell_data 생성
        for inventory_item in inventory_items:
            for shop in shops:
                item = inventory_item.item  # inventory_item에서 item 가져오기
                # 각 상점에 대한 가격 계산 (shopitemmanagement에서 첫 번째 항목의 가격을 가져옴)
                shop_price_entry = Shopitemmanagement.objects.filter(item=item, shop=shop).first()

                if shop_price_entry:
                    shop_price = int(round(shop_price_entry.price * 0.8,2))  # 0.8 곱한 가격 저장
                    inventory_sell_data.append({
                        'inventory_item': inventory_item,
                        'shop': shop,
                        'shop_price': shop_price,
                    })
                else:
                    # 가격이 없는 상점은 포함하지 않음
                    continue
    else:
        data['player'] = None

    # data에 shop과 shop_item_managements 추가
    data.update({
        'shop_infos': shop_infos,
        'shop_item_managements': shop_item_managements,
        'inventory_sell_data': inventory_sell_data,
        'transactionhistories': transactionhistories
    })

    return render(request, 'main/mainpage.html', data)

def login(request):
    if request.method == 'POST':
        nickname = request.POST.get('nickname')
        password = request.POST.get('password')

        try:
            # 닉네임으로 플레이어 검색
            player = Player.objects.get(nickname=nickname)

            # 비밀번호 검증
            if check_password(password, player.password):
                # 로그인 성공 시 세션에 player_id 저장
                request.session['player_id'] = player.id
                return redirect('main:mainpage')
            else:
                # 비밀번호가 틀린 경우
                messages.error(request, "비밀번호가 일치하지 않습니다.")
        except Player.DoesNotExist:
            # 닉네임이 존재하지 않는 경우
            messages.error(request, "존재하지 않는 닉네임입니다.")

    return redirect('main:mainpage')

def signin(request):
    if request.method == 'POST':
        nickname = request.POST.get('nickname')
        password = request.POST.get('password')
        # 닉네임이 이미 존재하는지 확인
        if Player.objects.filter(nickname=nickname).exists():
            # 이미 존재하면 알림 메시지 추가
            messages.error(request, "이미 존재하는 닉네임입니다. 다른 닉네임을 사용해 주세요.")
        else:
            # 새로운 플레이어 생성
            new_player = Player.objects.create(nickname=nickname, level=1, health=100)
            new_player.password = make_password(password)  # 비밀번호를 해시화하여 저장.password = make_password(password)
            new_player.save()
            new_player_currency = Playercurrency.objects.create(player_id=new_player.id, amount=0)
            new_player_inventory = Inventory.objects.create(player_id=new_player.id, capacity=50)
            messages.success(request, f"플레이어 {nickname}가 성공적으로 생성되었습니다.")

            request.session['player_id'] = new_player.id
            return redirect('main:mainpage')
    return render(request, 'main/mainpage.html')

def staffpage(request):
    return render(request, 'main/adminpage.html')

def logout(request):
    request.session.pop('player_id', None)
    return redirect('main:mainpage')

def player_custom(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        player = Player.objects.get(id=request.session['player_id'])

        # 액션에 따라 데이터 수정
        if action == 'gold_inc':
            player.playercurrency.amount += 10
        elif action == 'gold_dec':
            player.playercurrency.amount -= 10

        # 변경사항 저장
        player.save()
        player.playercurrency.save()

    return redirect('main:mainpage')
"""
def buy_item1(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get(f'quantity_{item_id}', 1))
        player = Player.objects.get(id=request.session['player_id'])
        inventory = Inventory.objects.get(player_id=player.id)
        total_quantity = sum(Inventoryitem.objects.filter(inventory_player_id=player.id).values_list('quantity', flat=True))
        if inventory.capacity < total_quantity + quantity :
            messages.error(request, "인벤토리 공간이 부족합니다.")
        else:
            try:
                # 아이템 정보 가져오기
                shop_item = Shopitemmanagement.objects.get(item_id=item_id)
                total_price = shop_item.price * quantity

                # 가격 및 재고 확인
                if player.playercurrency.amount >= total_price:
                    if shop_item.stockquantity >= quantity:
                        # 재화 차감
                        player.playercurrency.amount -= total_price
                        player.playercurrency.save()

                        # 재고 차감
                        shop_item.stockquantity -= quantity
                        shop_item.save()
                        
                        updated_rows = Inventoryitem.objects.filter(
                            inventory_player_id=player.id,
                            item_id=item_id
                        ).update(quantity=F('quantity') + quantity)

                        if updated_rows == 0:
                            # 만약 기존 아이템이 없으면 새로 생성
                            Inventoryitem.objects.create(
                                inventory_player_id=player.id,
                                item_id=item_id,
                                quantity=quantity
                            )
                        item = Item.objects.get(id=item_id)
                        transaction = Transactionhistory(
                            player=player.playercurrency,
                            item=item,
                            shop=shop_item.shop,
                            transactiontype='buy', 
                            quantity=quantity,
                            date=timezone.now()
                        )
                        transaction.save()
                    else:
                        messages.error(request, "재고가 부족합니다.")
                else:
                    messages.error(request, "보유 재화가 부족합니다.")

            except Shopitemmanagement.DoesNotExist:
                messages.error(request, "존재하지 않는 아이템입니다.")

    return redirect('main:mainpage')
"""
"""
def sell_item(request):
    if request.method == 'POST':
        player_id = request.POST.get('player_id')
        item_id = request.POST.get('item_id')
        shop_id = request.POST.get('shop_id')
        if shop_id == 0:
            messages.error(request, "판매할 상점을 선택하세요.")
        quantity = int(request.POST.get('quantity'))
        print(quantity)
        inventory_item = get_object_or_404(Inventoryitem, inventory_player=player_id, item=item_id)
        shop = get_object_or_404(Shop, id=shop_id)
        
        # 해당 아이템의 가격을 Shopitemmanagement에서 가져오기
        shop_price_entry = Shopitemmanagement.objects.filter(item_id=item_id, shop=shop).first()
        if not shop_price_entry:
            return JsonResponse({'error': '판매 가격을 찾을 수 없습니다.'}, status=400)
        
        shop_price = shop_price_entry.price * 0.8
        
        # Playercurrency 업데이트 (판매한 금액만큼 추가)
        player_currency = Playercurrency.objects.get(player=player_id)
        total_price = shop_price * quantity
        player_currency.amount += total_price
        player_currency.save()

        # 판매된 수량만큼 차감
        inventory_item = Inventoryitem.objects.filter(inventory_player=player_id, item=item_id)

        # 수량을 차감하고, 0 이하일 경우 삭제
        if inventory_item.exists():
            inventory_item.update(quantity=F('quantity') - quantity)  # 수량 차감
            
            # 수량이 0 이하일 경우 삭제
            inventory_item.filter(quantity__lte=0).delete()

        # Shopitemmanagement에서 해당 상점의 수량 증가 또는 생성
        shop_item_management, created = Shopitemmanagement.objects.get_or_create(
            item_id=item_id, 
            shop=shop,
            defaults={'stockquantity': 0}  # 없으면 stockquantity를 0으로 설정
        )

        # 수량을 증가시킴
        shop_item_management.stockquantity += quantity
        shop_item_management.save()

        player = Player.objects.get(id=player_id)
        item = Item.objects.get(id=item_id)
        transaction = Transactionhistory(
            player=player.playercurrency,
            item=item,
            shop=shop,
            transactiontype='sell',
            quantity=quantity,
            date=timezone.now()
        )
        transaction.save()

        return redirect('main:mainpage')  # 판매 후 다시 메인 페이지로 리다이렉트
    return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)
"""
def get_sell_price(request):
    item_id = request.GET.get('item_id')
    shop_id = request.GET.get('shop_id')

    try:
        item = get_object_or_404(Item, id=item_id)
        shop = get_object_or_404(Shop, id=shop_id)

        # Shopitemmanagement에서 가격을 가져와 0.8을 곱함
        shop_item_management = Shopitemmanagement.objects.filter(item=item, shop=shop).first()
        
        if shop_item_management:
            sell_price = int(round(shop_item_management.price * 0.8, 2))
        else:
            sell_price = None

        return JsonResponse({'shop_price': sell_price})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def create_item(request):
    if request.method == 'POST':
        # 입력 값 가져오기
        item_type = request.POST.get('item_type')
        item_name = request.POST.get('item_name')
        item_effect = request.POST.get('item_effect')
        shop_id = request.POST.get('shop_id')
        base_quantity = request.POST.get('base_quantity')
        base_price = request.POST.get('base_price')
        price_fluctuation = request.POST.get('price_fluctuation')

        # SQL 쿼리 실행
        with connection.cursor() as cursor:
            # Item 생성
            cursor.execute(
                "INSERT INTO Item (Type, Name, Effect) VALUES (%s, %s, %s)",
                [item_type, item_name, item_effect]
            )
            cursor.execute("SELECT LAST_INSERT_ID()")
            new_item_id = cursor.fetchone()[0]

            # ItemPriceManagement 생성
            cursor.execute(
                "INSERT INTO ItemPriceManagement (BaseQuantity, BasePrice, PriceFluctuation) VALUES (%s, %s, %s)",
                [base_quantity, base_price, price_fluctuation]
            )
            cursor.execute("SELECT LAST_INSERT_ID()")
            price_management_id = cursor.fetchone()[0]

            # Price 계산: (base_quantity * base_price) / (base_quantity * price_fluctuation)
            calculated_price = (int(base_quantity) * int(base_price)) / (int(base_quantity) * float(price_fluctuation))
            
            # ShopItemManagement 생성
            cursor.execute(
                """
                INSERT INTO ShopItemManagement (Item_ID, PriceManagement_ID, Shop_ID, StockQuantity, Price) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                [new_item_id, price_management_id, shop_id, base_quantity, calculated_price]
            )

        # 성공 메시지
        messages.success(request, f"아이템 {item_name}가 성공적으로 생성되었습니다. (아이템 ID: {new_item_id})")

    return render(request, 'main/adminpage.html')

def buy_item(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        shop_id = request.POST.get('shop_id')
        quantity = int(request.POST.get(f'quantity_{item_id}', 1))
        player = Player.objects.get(id=request.session['player_id'])
        player_id = player.id

        try:
            # 트랜잭션 시작
            with connection.cursor() as cursor:
                cursor.execute("START TRANSACTION;")  # 트랜잭션 시작
                send_transaction_status(request, "트랜잭션 시작", 10)

                # 1. 인벤토리 용량 확인
                cursor.execute("""
                    SELECT SUM(quantity) 
                    FROM InventoryItem 
                    WHERE Inventory_Player_ID = %s
                """, [player_id])
                total_quantity = cursor.fetchone()[0] or 0

                inventory = player.inventory
                if inventory.capacity < total_quantity + quantity:
                    messages.error(request, "인벤토리 공간이 부족합니다.")
                    cursor.execute("ROLLBACK;")  # 트랜잭션 롤백
                    return redirect('main:mainpage')

                # 2. 아이템 가격 및 재고 확인 (여기서 락 추가)
                cursor.execute("""
                    SELECT Price, StockQuantity 
                    FROM ShopItemManagement 
                    WHERE Item_ID = %s AND Shop_ID = %s
                    FOR UPDATE  -- 재고에 락을 걸어 다른 트랜잭션이 동시에 수정하지 못하도록 함
                """, [item_id, shop_id])
                shop_item_data = cursor.fetchone()

                if shop_item_data is None:
                    messages.error(request, "존재하지 않는 아이템입니다.")
                    cursor.execute("ROLLBACK;")  # 트랜잭션 롤백
                    return redirect('main:mainpage')

                price, stockquantity = shop_item_data
                total_price = price * quantity

                # 3. 플레이어 재화 차감 (보유 재화가 충분한지 확인)
                cursor.execute("""
                    SELECT Amount 
                    FROM PlayerCurrency 
                    WHERE Player_ID = %s
                """, [player_id])
                player_currency = cursor.fetchone()[0]

                if player_currency < total_price:
                    messages.error(request, "보유 재화가 부족합니다.")
                    cursor.execute("ROLLBACK;")  # 트랜잭션 롤백
                    return redirect('main:mainpage')

                # 4. 재화 차감
                cursor.execute("""
                    UPDATE PlayerCurrency 
                    SET Amount = Amount - %s 
                    WHERE Player_ID = %s
                """, [total_price, player_id])

                # 5. 상점 재고 차감 (재고가 충분한 경우)
                if stockquantity < quantity:
                    messages.error(request, "재고가 부족합니다.")
                    cursor.execute("ROLLBACK;")  # 트랜잭션 롤백
                    return redirect('main:mainpage')

                cursor.execute("""
                    UPDATE ShopItemManagement 
                    SET StockQuantity = StockQuantity - %s 
                    WHERE Item_ID = %s AND Shop_ID = %s
                """, [quantity, item_id, shop_id])

                # 6. 인벤토리 업데이트 (기존 아이템이 있다면 수량 증가)
                cursor.execute("""
                    UPDATE InventoryItem 
                    SET Quantity = Quantity + %s
                    WHERE Inventory_Player_ID = %s AND Item_ID = %s
                """, [quantity, player_id, item_id])

                # 7. 인벤토리 아이템이 없으면 새로 추가
                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO InventoryItem (Inventory_Player_ID, Item_ID, Quantity) 
                        VALUES (%s, %s, %s)
                    """, [player_id, item_id, quantity])
                print(shop_id)
                # 8. 거래 기록 저장
                cursor.execute("""
                    INSERT INTO TransactionHistory (Player_ID, Item_ID, Shop, TransactionType, Quantity, Date) 
                    VALUES (%s, %s, %s, 'buy', %s, NOW())
                """, [player_id, item_id, shop_id, quantity])

                # 트랜잭션 커밋
                cursor.execute("COMMIT;")  # 트랜잭션 커밋
                send_transaction_status(request, "트랜잭션 완료", 100)
            return redirect('main:mainpage')

        except Exception as e:
            # 오류가 발생하면 롤백
            with connection.cursor() as cursor:
                cursor.execute("ROLLBACK;")  # 트랜잭션 롤백
            messages.error(request, f"오류가 발생했습니다: {str(e)}")
            return redirect('main:mainpage')

    return redirect('main:mainpage')

def sell_item(request):
    if request.method == 'POST':
        player_id = request.POST.get('player_id')
        item_id = request.POST.get('item_id')
        shop_id = request.POST.get('shop_id')
        
        if int(shop_id) == 0:
            messages.error(request, f"판매할 상점을 선택하세요.")
            return redirect('main:mainpage')

        quantity = int(request.POST.get('quantity'))
        
        try:
            # 트랜잭션 시작
            with connection.cursor() as cursor:
                cursor.execute("START TRANSACTION;")  # 트랜잭션 시작
                send_transaction_status(request, "트랜잭션 시작", 10)
                
                # 1. InventoryItem에서 플레이어와 아이템 확인
                cursor.execute("""
                    SELECT Quantity FROM InventoryItem
                    WHERE Inventory_Player_ID = %s AND Item_ID = %s
                    FOR UPDATE
                """, [player_id, item_id])
                inventory_item = cursor.fetchone()
                
                if not inventory_item:
                    return JsonResponse({'error': '아이템을 찾을 수 없습니다.'}, status=400)
                
                # 2. Shop 확인
                cursor.execute("SELECT ID FROM Shop WHERE ID = %s", [shop_id])
                if not cursor.fetchone():
                    return JsonResponse({'error': '상점을 찾을 수 없습니다.'}, status=400)
                
                # 3. ShopItemManagement에서 아이템 가격 확인
                cursor.execute("""
                    SELECT Price FROM ShopItemManagement
                    WHERE Item_ID = %s AND Shop_ID = %s
                """, [item_id, shop_id])
                shop_price_entry = cursor.fetchone()
                
                if not shop_price_entry:
                    return JsonResponse({'error': '판매 가격을 찾을 수 없습니다.'}, status=400)
                
                shop_price = int(shop_price_entry[0] * 0.8)
                
                # 4. PlayerCurrency 업데이트
                total_price = shop_price * quantity
                cursor.execute("""
                    UPDATE PlayerCurrency
                    SET Amount = Amount + %s
                    WHERE Player_ID = %s
                """, [total_price, player_id])
                
                # 5. InventoryItem 수량 차감 및 삭제
                cursor.execute("""
                    UPDATE InventoryItem
                    SET Quantity = Quantity - %s
                    WHERE Inventory_Player_ID = %s AND Item_ID = %s
                """, [quantity, player_id, item_id])

                cursor.execute("""
                    DELETE FROM InventoryItem
                    WHERE Quantity <= 0 AND Inventory_Player_ID = %s AND Item_ID = %s
                """, [player_id, item_id])
                
                # 6. ShopItemManagement 수량 증가 또는 생성
                cursor.execute("""
                    UPDATE ShopItemManagement
                    SET StockQuantity = StockQuantity + %s
                    WHERE Item_ID = %s AND Shop_ID = %s
                """, [quantity, item_id, shop_id])
                
                # 7. TransactionHistory 기록 추가
                cursor.execute("""
                    INSERT INTO TransactionHistory (Player_ID, Item_ID, Shop, TransactionType, Quantity, Date)
                    VALUES (%s, %s, %s, 'sell', %s, %s)
                """, [player_id, item_id, shop_id, quantity, timezone.now()])

                # 트랜잭션 커밋
                cursor.execute("COMMIT;")  # 트랜잭션 커밋
                send_transaction_status(request, "트랜잭션 완료", 100)
            return redirect('main:mainpage')

        except Exception as e:
            # 오류가 발생하면 롤백
            with connection.cursor() as cursor:
                cursor.execute("ROLLBACK;")  # 트랜잭션 롤백
            messages.error(request, f"오류가 발생했습니다: {str(e)}")
            return redirect('main:mainpage')

    return redirect('main:mainpage')

def send_transaction_status(request, message="", progress=0):
    # 상태 메시지와 진행률을 JSON 형식으로 반환
    response_data = {
        'message': message,
        'progress': progress  # 진행 상황 (0~100)
    }
    return JsonResponse(response_data)