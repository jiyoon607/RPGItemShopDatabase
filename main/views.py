from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import F
from django.utils import timezone

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
    inventory_sell_data=[]
    shop_infos = []
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
        for inventory_item in inventory_items:
            for shop in shops:
                item = Item.objects.get(id=inventory_item.item.id)
                # 각 상점에 대한 가격 계산 (shopitemmanagement_set에서 첫 번째 항목의 가격을 가져옴)
                shop_price = Shopitemmanagement.objects.filter(item=item, shop=shop).first()
                if shop_price:
                    shop_price = shop_price.price * 0.8  # 0.8 곱한 가격 저장
                else:
                    shop_price = None  # 가격이 없으면 None
                inventory_sell_data.append({
                    'inventory_item': inventory_item,
                    'shop': shop,
                    'shop_price': shop_price,
                })
    else:
        data['player'] = None
    # data에 shop과 shop_item_managements 추가
    data.update({
        'shop_infos': shop_infos,
        'shop_item_managements': shop_item_managements,
        'inventory_sell_data':inventory_sell_data,
        'transactionhistories':transactionhistories
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
        if action == 'health_inc':
            player.health += 10
        elif action == 'health_dec':
            player.health -= 10
        elif action == 'level_inc':
            player.level += 1
        elif action == 'level_dec':
            player.level -= 1
        elif action == 'gold_inc':
            player.playercurrency.amount += 10
        elif action == 'gold_dec':
            player.playercurrency.amount -= 10

        # 변경사항 저장
        player.save()
        player.playercurrency.save()

    return redirect('main:mainpage')

def buy_item(request):
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


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def get_sell_price(request):
    item_id = request.GET.get('item_id')
    shop_id = request.GET.get('shop_id')

    try:
        item = get_object_or_404(Item, id=item_id)
        shop = get_object_or_404(Shop, id=shop_id)

        # Shopitemmanagement에서 가격을 가져와 0.8을 곱함
        shop_item_management = Shopitemmanagement.objects.filter(item=item, shop=shop).first()
        
        if shop_item_management:
            sell_price = shop_item_management.price * 0.8
        else:
            sell_price = None

        return JsonResponse({'shop_price': sell_price})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

from django.db import connection

def buy_item(player_id, item_id, quantity, total_cost):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                START TRANSACTION;

                -- 통화 업데이트 (구매 예시: player_id가 1번인 플레이어의 통화에서 500 차감)
                UPDATE player
                SET currency = currency - 500
                WHERE id = 1;

                -- 플레이어 통화가 0보다 작은 경우 롤백
                IF ROW_COUNT() = 0 OR (SELECT currency FROM player WHERE id = 1) < 0 THEN
                    ROLLBACK;
                    SELECT 'Insufficient funds' AS error_message;
                    LEAVE;
                END IF;

                -- 아이템 수량 업데이트 (구매 시 수량 증가 예시)
                UPDATE inventoryitem
                SET quantity = quantity + 3
                WHERE inventory_player_id = 1 AND item_id = 1;

                -- 판매 시 수량 검증 및 업데이트 예시 (수량이 부족한 경우 롤백)
                IF (SELECT quantity FROM inventoryitem WHERE inventory_player_id = 1 AND item_id = 1) < 3 THEN
                    ROLLBACK;
                    SELECT 'Insufficient item stock' AS error_message;
                    LEAVE;
                END IF;

                -- 수량이 0이 될 경우 예외 처리
                IF (SELECT quantity FROM inventoryitem WHERE inventory_player_id = 1 AND item_id = 1) = 0 THEN
                    ROLLBACK;
                    SELECT 'Cannot delete item from inventory' AS error_message;
                    LEAVE;
                END IF;

                COMMIT;

                SELECT 'Transaction completed successfully' AS success_message;

            """)
        return {"status": "success", "message": "Purchase completed."}
    except Exception as e:
        return {"status": "error", "message": str(e)}