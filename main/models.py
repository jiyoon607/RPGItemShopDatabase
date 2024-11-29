# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models

class Item(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    type = models.CharField(db_column='Type', max_length=50)  # Field name made lowercase.
    name = models.CharField(db_column='Name', unique=True, max_length=100)  # Field name made lowercase.
    effect = models.TextField(db_column='Effect', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Item'

class Player(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    nickname = models.CharField(db_column='Nickname', unique=True, max_length=50)  # Field name made lowercase.
    level = models.IntegerField(db_column='Level')  # Field name made lowercase.
    health = models.IntegerField(db_column='Health')  # Field name made lowercase.
    password = models.CharField(db_column='Password', max_length=20)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Player'

class Inventory(models.Model):
    player = models.OneToOneField('Player', models.DO_NOTHING, db_column='Player_ID', primary_key=True)  # Field name made lowercase.
    capacity = models.IntegerField(db_column='Capacity')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Inventory'

class Inventoryitem(models.Model):
    inventory_player = models.OneToOneField('Inventory', models.DO_NOTHING, db_column='Inventory_Player_ID', primary_key=True)  # Field name made lowercase. The composite primary key (Inventory_Player_ID, Item_ID) found, that is not supported. The first column is selected.
    item = models.ForeignKey('Item', models.DO_NOTHING, db_column='Item_ID')  # Field name made lowercase.
    quantity = models.IntegerField(db_column='Quantity')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'InventoryItem'
        unique_together = (('inventory_player', 'item'),)

class Itempricemanagement(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    basequantity = models.IntegerField(db_column='BaseQuantity')  # Field name made lowercase.
    baseprice = models.IntegerField(db_column='BasePrice')  # Field name made lowercase.
    pricefluctuation = models.FloatField(db_column='PriceFluctuation')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ItemPriceManagement'

class Playercurrency(models.Model):
    player = models.OneToOneField('Player', models.DO_NOTHING, db_column='Player_ID', primary_key=True)  # Field name made lowercase.
    amount = models.IntegerField(db_column='Amount')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'PlayerCurrency'

class Shop(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    name = models.CharField(db_column='Name', max_length=100)  # Field name made lowercase.
    location = models.CharField(db_column='Location', max_length=100)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Shop'

class Shopitemmanagement(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    item = models.ForeignKey('Item', models.DO_NOTHING, db_column='Item_ID')  # Field name made lowercase.
    shop = models.ForeignKey('Shop', models.DO_NOTHING, db_column='Shop_ID')  # Field name made lowercase.
    pricemanagement = models.ForeignKey('Itempricemanagement', models.DO_NOTHING, db_column='PriceManagement_ID')  # Field name made lowercase.
    stockquantity = models.IntegerField(db_column='StockQuantity')  # Field name made lowercase.
    price = models.IntegerField(db_column='Price')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ShopItemManagement'

class Transactionhistory(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    player = models.ForeignKey('Playercurrency', models.DO_NOTHING, db_column='Player_ID')  # Field name made lowercase.
    item = models.ForeignKey('Item', models.DO_NOTHING, db_column='Item_ID', blank=True, null=True)  # Field name made lowercase.
    transactiontype = models.CharField(db_column='TransactionType', max_length=4)  # Field name made lowercase.
    quantity = models.IntegerField(db_column='Quantity')  # Field name made lowercase.
    date = models.DateTimeField(db_column='Date', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'TransactionHistory'