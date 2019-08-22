from __future__ import division
import urllib
import json
from time import sleep
from datetime import datetime
from poloniex import Poloniex
from bittrex.bittrex import Bittrex


polo = Poloniex()


# poloniex key ve anahtar
polo.key    = ''
polo.secret = ''
# bittrex key ve anahtar
my_bittrex = Bittrex("",
                     "")

# islem yapilacak coinler
bittrex_market = ['BTC-DGB', 'BTC-SC']
poloniex_market = ['BTC_DGB', 'BTC_SC']
zorluk = 15                             # binde oran DIKKAT. kayip ile beraber kullanilacak
islem_ucreti = 0.0012                   # her bir islemde BTC bazinda kullanilacak ucret
tekrar = 150                            # islemin tekrar sayisi
kayip = 2                               # binde oraninda kayip. emrin garantisi

#!!!!!!!!!!!!! ONEMLI !!!!!!!!!!!!!!!!!!!!
# herbir markette coinin alim ve satim degerleri kontrol edilir.
# marketlerdeki alim fiyatindan satim, satim fiyatindan alim yapilacak sekilde islemler yapilir.
# iki market arasindaki makas zorluk/1000'den buyuk oldugunda her iki markette emir verilir.
# kayip/1000 kadar alim fiyati asagi cekilir
# kayip/1000 kadar satim fiyati yukari cekilir

i = 0


print "Zorluk seviyesi:\t", zorluk, "\tIslem basi ucret:\t", islem_ucreti, "\tKayip:\t", kayip
print "Tekrar Sayisi:\t", tekrar

# Baslangic oncesi cuzdan verileri
balance = polo.returnBalances()
print datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "CUZDAN VERILERI"

btrx_wallet = float(my_bittrex.get_balance('BTC')['result']['Available'])

polo_wallet = float(balance['BTC'])
baslangic_toplam = btrx_wallet + polo_wallet
print "Bittrex BTC :\t", btrx_wallet
print "Poloniex BTC :\t", polo_wallet
print "Toplam BTC :\t", baslangic_toplam
print "-------"
for bittrex_currency, poloniex_currency in zip(bittrex_market, poloniex_market):
    currency = bittrex_currency[4:]

    btrx_wallet_c = float(my_bittrex.get_balance(currency)['result']['Available'])
    print "Bittrex", currency, ":\t", btrx_wallet_c

    polo_wallet_c = float(balance[currency])
    print "Poloniex", currency, ":\t", polo_wallet_c
    print currency, "toplam :\t", polo_wallet_c + btrx_wallet_c
    print "-------"

sleep(1)
# Cuzdan verileri sonu

# Programin Baslangici
while i < tekrar:
    print ""
    print "Islem:\t", i + 1, "\tbtrx\t\tpolo\t\t", datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for bittrex_currency, poloniex_currency in zip(bittrex_market, poloniex_market):
        cuzdan_kontrol = 0
        market_kontrol = 0
        while True:
            try:
                # bittrex fiyati
                url_bittrex = "https://bittrex.com/api/v1.1/public/getticker?market=" + bittrex_currency
                response_bittrex = urllib.urlopen(url_bittrex)
                data_bittrex = json.loads(response_bittrex.read())
                ba = float(data_bittrex['result']['Bid'])
                bs = float(data_bittrex['result']['Ask'])

                # poloniex fiyatlari, tum veri cekildi. asagida markete gore ayristirma yapilacak
                url_poloniex = "https://poloniex.com/public?command=returnTicker"
                response_poloniex = urllib.urlopen(url_poloniex)
                data_poloniex = json.loads(response_poloniex.read())

                pa = float(data_poloniex[poloniex_currency]["highestBid"])
                ps = float(data_poloniex[poloniex_currency]["lowestAsk"])

                # hesaplamalar
                btrxavantaj = (pa - bs) / pa * 1000
                poloavantaj = (ba - ps) / ba * 1000

                currency = bittrex_currency[4:]
                print currency, "\t", btrxavantaj, "\t\t", poloavantaj

                market_kontrol = 1

                break
            except:
                continue

        currency = bittrex_currency[4:]

# ustteki dongu fiyatlari dogru cekmeden sonuclanmiyor
        if market_kontrol == 1:
            # walletta musait coin olup olmadigina bakilacak, avantaj varsa emir verilecek
            if btrxavantaj > zorluk or poloavantaj > zorluk:
                try:
                    btrx_wallet = float(my_bittrex.get_balance('BTC')['result']['Available'])
                    btrx_wallet_c = float(my_bittrex.get_balance(currency)['result']['Available'])

                    polo_wallet_c = float(balance[currency])
                    polo_wallet = float(balance['BTC'])

                    amount_alis = islem_ucreti / bs                     # alinacak coin miktari
                    amount_satis = amount_alis * 0.9975                 # satilacak coin miktari

                    cuzdan_kontrol = 1
                except:
                    cuzdan_kontrol = 0
                    continue
            if cuzdan_kontrol == 1:
                if btrxavantaj > zorluk and btrx_wallet > islem_ucreti and polo_wallet_c * pa > islem_ucreti:
                    try:

                        pa = pa * (1 - (kayip + (btrxavantaj - zorluk)) / 1000)
                        bs = bs * (1 + (kayip + (btrxavantaj - zorluk)) / 1000)

                        polo.sell(poloniex_currency, pa, amount_satis)
                        order_s = my_bittrex.buy_limit(bittrex_currency, amount_alis, bs)

                        print btrxavantaj, "\tBITTREX ALIS\t", bs, "\n\t\tPOLO SATIS\t", pa
                        print datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        # emir kontrolu. islem sonra devam edecek (bittrex)
                        while True:
                            try:
                                kontrol = my_bittrex.get_order(order_s['result']['uuid'])
                                if kontrol['result']['IsOpen'] == False:
                                    print "bittrex alim emri gerceklesti"

                                    break
                            except:
                                print "bittrex alim emir kontrol hatasi"
                                sleep(1)

                        while True:
                            try:
                                a = polo.returnOpenOrders()
                                if a[poloniex_currency]:
                                    continue
                                else:
                                    print "polo satim emri gerceklesti"

                                    break
                            except:
                                print "polo satim emri kontrol hatasi"
                                sleep(1)

                        i = i + 1

                    except:
                        print btrxavantaj, "\tBITTREX ALIS\t", bs, "\n\t\tPOLO SATIS\t", pa, "\tEmir verilemedi"
                        print datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        continue

                if poloavantaj > zorluk and polo_wallet > islem_ucreti and btrx_wallet_c * ba > islem_ucreti:
                    try:

                        ps = ps * (1 + (kayip + (poloavantaj - zorluk)) / 1000)
                        ba = ba * (1 - (kayip + (poloavantaj - zorluk)) / 1000)

                        order_s = my_bittrex.sell_limit(bittrex_currency, amount_satis, ba)
                        polo.buy(poloniex_currency, ps, amount_alis)

                        print poloavantaj, "\tPOLO ALIS\t", ps, "\n\t\tBITTREXSATIS\t", ba
                        print datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        # emir kontrolu. islem sonra devam edecek (bittrex)
                        while True:
                            try:
                                kontrol = my_bittrex.get_order(order_s['result']['uuid'])
                                if kontrol['result']['IsOpen'] == False:
                                    print "bittrex satim emri gerceklesti"

                                    break
                            except:
                                print "bittrex satim emi kontrol hatasi"
                                sleep(1)

                        while True:
                            try:
                                a = polo.returnOpenOrders()
                                if a[poloniex_currency]:
                                    continue
                                else:
                                    print "polo alim emri gerceklesti"

                                    break
                            except:
                                print "polo alim emri kontrol hatasi"
                                sleep(1)

                        i = i + 1

                    except:
                        print poloavantaj, "\tPOLO ALIS\t", ps, "\n\t\tBITTREXSATIS\t", ba, "\tEmir verilemedi"
                        print datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        continue

# Program bitis
# Bitis cuzdan verileri
balance = polo.returnBalances()
print datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "CUZDAN VERILERI"

btrx_wallet = float(my_bittrex.get_balance('BTC')['result']['Available'])
polo_wallet = float(balance['BTC'])
bitis_toplam = btrx_wallet + polo_wallet
print "Bittrex BTC :\t", btrx_wallet
print "Poloniex BTC :\t", polo_wallet
print "Bitis Toplam BTC :\t", bitis_toplam
print "--------"
for bittrex_currency, poloniex_currency in zip(bittrex_market, poloniex_market):
    currency = bittrex_currency[4:]

    btrx_wallet_c = float(my_bittrex.get_balance(currency)['result']['Available'])
    print "Bittrex", currency, ":\t", btrx_wallet_c

    polo_wallet_c = float(balance[currency])
    print "Poloniex", currency, ":\t", polo_wallet_c
    print currency, "toplam :\t", polo_wallet_c + btrx_wallet_c
    print "--------"
net_kar = bitis_toplam - baslangic_toplam
print "Toplam Kar BTC:\t", net_kar
# Cuzdan verileri sonu
