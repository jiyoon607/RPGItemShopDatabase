from django.urls import path
from .views import *

app_name = "main"
urlpatterns = [
    path('', mainpage, name='mainpage'),
    path('login/', login, name="login"),
    path('signin/', signin, name='signin'),
    path('logout/', logout, name='logout'),
    path('player-custom/', player_custom, name='player-custom'),
    path('buy-item/', buy_item, name='buy-item'),
]