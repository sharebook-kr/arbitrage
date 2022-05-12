from re import I
from tkinter import W
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import sys
import pykorbit
import pyupbit

#with open("korbit.key") as f:
#    lines = f.readlines()
#    key = lines[0].strip()
#    secret = lines[1].strip()
#korbit = pykorbit.Korbit(key, secret)
#
#with open("upbit.key") as f:
#    lines = f.readlines()
#    access = lines[0].strip()
#    secret = lines[1].strip()
#upbit = pyupbit.Upbit(access, secret)


class KorbitWS(QThread):
    poped = pyqtSignal(dict)

    def run(self):
        self.wm = pykorbit.WebSocketManager(['orderbook:xrp_krw'])
        while True:
            data = self.wm.get()
            self.poped.emit(data)

    def terminate(self) -> None:
        self.wm.terminate()


class UpbitWS(QThread):
    poped = pyqtSignal(dict)

    def run(self):
        self.wm = pyupbit.WebSocketManager(type="orderbook", codes=["KRW-XRP"])
        while True:
            data = self.wm.get()
            self.poped.emit(data)

    def terminate(self) -> None:
        self.wm.terminate()


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(200, 200, 700, 700)
        self.setWindowTitle("Arbitrage Bot v1.0")

        self.korbit_started = False
        self.korbit_ask0_price = 0
        self.korbit_ask1_price = 0
        self.korbit_ask0_quantity = 0
        self.korbit_ask1_quantity = 0
        self.korbit_bid0_price = 0
        self.korbit_bid1_price = 0
        self.korbit_bid0_quantity = 0
        self.korbit_bid1_quantity = 0

        self.upbit_ask0_price = 0
        self.upbit_ask1_price = 0
        self.upbit_ask0_quantity = 0
        self.upbit_ask1_quantity = 0
        self.upbit_bid0_price = 0
        self.upbit_bid1_price = 0
        self.upbit_bid0_quantity = 0
        self.upbit_bid1_quantity = 0

        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.hbox = QHBoxLayout()
        self.plain_text = QPlainTextEdit()
        layout.addLayout(self.hbox)
        layout.addWidget(self.plain_text)

        self.left_vbox = QVBoxLayout()
        self.right_vbox = QVBoxLayout()
        self.hbox.addLayout(self.left_vbox)
        self.hbox.addLayout(self.right_vbox)

        self.add_table_widget()
        self.create_ws_threads()

        # left vbox
        label = QLabel("코빗 (Maker: -0.05%, Taker: 0.25%)")
        self.left_vbox.addWidget(label)
        self.left_vbox.addWidget(self.table_widget1)

        # right vbox
        label = QLabel("업비트 (Maker: 0.05%, Taker: 0.05%)")
        self.right_vbox.addWidget(label)
        self.right_vbox.addWidget(self.table_widget2)

        self.setCentralWidget(widget)

    def add_table_widget(self):
        # korbit
        self.table_widget1 = QTableWidget(self)
        self.table_widget1.setColumnCount(3)
        self.table_widget1.setRowCount(10)
        self.table_widget1.verticalHeader().setVisible(False)
        self.table_widget1.horizontalHeader().setVisible(False)
        #self.table_widget1.setColumnWidth(0, int(self.table_widget1.width() * 0.4))
        #self.table_widget1.setColumnWidth(1, int(self.table_widget1.width() * 0.2))
        #self.table_widget1.setColumnWidth(2, int(self.table_widget1.width() * 0.4))

        # upbit
        self.table_widget2 = QTableWidget(self)
        self.table_widget2.setColumnCount(3)
        self.table_widget2.setRowCount(10)
        self.table_widget2.verticalHeader().setVisible(False)
        self.table_widget2.horizontalHeader().setVisible(False)
        #self.table_widget2.setColumnWidth(0, int(self.table_widget2.width() * 0.4))
        #self.table_widget2.setColumnWidth(1, int(self.table_widget2.width() * 0.2))
        #self.table_widget2.setColumnWidth(2, int(self.table_widget2.width() * 0.4))

    def create_ws_threads(self):
        self.wsc_upbit = UpbitWS()
        self.wsc_upbit.poped.connect(self.pop_upbit)
        self.wsc_upbit.start()

        self.wsc_korbit = KorbitWS()
        self.wsc_korbit.poped.connect(self.pop_korbit)
        self.wsc_korbit.start()

    def pop_korbit(self, data):
        try:
            # 1호가, 2호가 데이터 저장
            ask0 = data['data']['asks'][0]
            self.korbit_ask0_price = float(ask0["price"])
            self.korbit_ask0_quantity = float(ask0["amount"])

            ask1 = data['data']['asks'][1]
            self.korbit_ask1_price = float(ask1["price"])
            self.korbit_ask1_quantity = float(ask1["amount"])

            bid0 = data['data']['bids'][0]
            self.korbit_bid0_price = float(bid0["price"])
            self.korbit_bid0_quantity = float(bid0["amount"])

            bid1 = data['data']['bids'][1]
            self.korbit_bid1_price = float(bid1["price"])
            self.korbit_bid1_quantity = float(bid1["amount"])

            self.korbit_started = True

            # ask
            for i in range(5):
                ask = data['data']['asks'][i]
                ask_price = float(ask["price"])
                ask_quantity = float(ask["amount"])

                item = QTableWidgetItem(str(ask_price))
                item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
                self.table_widget1.setItem(4-i, 1, item)

                item = QTableWidgetItem(format(int(ask_quantity), ","))
                item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
                self.table_widget1.setItem(4-i, 0, item)
            # bid
            for i in range(5):
                bid = data['data']['bids'][i]
                bid_price = float(bid["price"])
                bid_quantity = float(bid["amount"])

                item = QTableWidgetItem(str(bid_price))
                item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
                self.table_widget1.setItem(5+i, 1, item)

                item = QTableWidgetItem(format(int(bid_quantity), ","))
                item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
                self.table_widget1.setItem(5+i, 2, item)
        except Exception as e:
            print(e)

    def run(self):
        if self.korbit_started:
            # 코빗이 싼 경우
            # 코빗의 지정가 매수가격(매도 1호가-0.1) < 업비트의 시장가 매도가격(매수 1호가)
            korbit_buy_hoga = self.korbit_ask0_price - 0.1
            if korbit_buy_hoga < self.upbit_bid0_price and korbit_buy_hoga != self.korbit_bid0_price:
                profit = self.upbit_bid0_price - korbit_buy_hoga
                quantity = 200

                # 업비트는 시장가 매도
                #upbit.sell_market_order("KRW-BTC", quantity)

                # 코빗은 지정가 매수
                #korbit.buy_limit_order("XRP", korbit_buy_hoga, quantity)

                text = f"코빗 지정가 매수 {korbit_buy_hoga:.1f} / 업비트 시장가 매도 {self.upbit_bid0_price:.1f} | 차익 {profit:.1f}"
                self.plain_text.appendPlainText(text)


            # 업비트가 싼 경우
            # 업비트의 시장가 매수가격(매도 1호가) < 코빗의 지정가 매도가격(매도 1호가+0.1)
            korbit_sell_hoga = self.korbit_ask0_price + 0.1
            if self.upbit_ask0_price < korbit_sell_hoga:
                profit = korbit_sell_hoga - self.upbit_ask0_price
                self.plain_text.appendPlainText(f"업비트 매수/코빗 매도 | 차익 {profit:.1f}")
                # 업비트는 시장가 매수

                # 코빗은 지정가 매도


    @pyqtSlot(dict)
    def pop_upbit(self, data):
        try:
            # 1호가, 2호가 데이터 저장
            orderbook0 = data['orderbook_units'][0]
            orderbook1 = data['orderbook_units'][1]

            self.upbit_ask0_price = float(orderbook0["ask_price"])
            self.upbit_ask0_quantity = float(orderbook0["ask_size"])
            self.upbit_ask1_price = float(orderbook1["ask_price"])
            self.upbit_ask1_quantity = float(orderbook1["ask_size"])

            self.upbit_bid0_price = float(orderbook0["bid_price"])
            self.upbit_bid0_quantity = float(orderbook0["bid_size"])
            self.upbit_bid1_price = float(orderbook1["bid_price"])
            self.upbit_bid1_quantity = float(orderbook1["bid_size"])

            self.run()

            # ask
            for i in range(5):
                orderbook = data['orderbook_units'][i]
                ask_price = float(orderbook["ask_price"])
                ask_quantity = float(orderbook["ask_size"])

                item = QTableWidgetItem(str(ask_price))
                item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
                self.table_widget2.setItem(4-i, 1, item)

                item = QTableWidgetItem(format(int(ask_quantity), ","))
                item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
                self.table_widget2.setItem(4-i, 0, item)

            # bid
            for i in range(5):
                orderbook = data['orderbook_units'][i]
                bid_price = float(orderbook["bid_price"])
                bid_quantity = float(orderbook["bid_size"])

                item = QTableWidgetItem(str(bid_price))
                item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
                self.table_widget2.setItem(5+i, 1, item)

                item = QTableWidgetItem(format(int(bid_quantity), ","))
                item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
                self.table_widget2.setItem(5+i, 2, item)
        except Exception as e:
            print(e)

    def closeEvent(self, event):
        self.wsc_upbit.terminate()
        self.wsc_korbit.terminate()
        return super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    app.exec_()