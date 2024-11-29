from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

from .models import *

# Create your views here.
def mainpage(request):
    shop = Shop.objects.get(id=1)
    shop_item_managements = Shopitemmanagement.objects.filter(shop=shop)
    player_id = request.session.get('player_id')
    player = None
    data = {}  # 초기 data를 빈 딕셔너리로 설정
    
    if player_id:
        player = Player.objects.get(id=player_id)
        data['player'] = player  # player 추가
    else:
        data['player'] = None
    # data에 shop과 shop_item_managements 추가
    data.update({
        'shop': shop,
        'shop_item_managements': shop_item_managements,
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
            messages.success(request, f"플레이어 {nickname}가 성공적으로 생성되었습니다.")

            request.session['player_id'] = new_player.id
            return redirect('main:mainpage')
    return render(request, 'main/mainpage.html')

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
        player = Player.objects.get(id=request.session['player_id'])

        # 아이템 조회
        try:
            shop_item = Shopitemmanagement.objects.get(item_id=item_id)

            # 가격과 재고 확인
            if player.playercurrency.amount >= shop_item.price:
                if shop_item.stockquantity > 0:
                    # 플레이어의 재화 차감
                    player.playercurrency.amount -= shop_item.price
                    player.playercurrency.save()

                    # 재고 차감
                    shop_item.stockquantity -= 1
                    shop_item.save()
                else:
                    messages.error(request, "재고가 부족합니다.")
            else:
                messages.error(request, "보유 재화가 부족합니다.")

        except Shopitemmanagement.DoesNotExist:
            messages.error(request, "존재하지 않는 아이템입니다.")

    return redirect('main:mainpage')  # 리다이렉트할 페이지