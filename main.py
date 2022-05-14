from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import sys
import pykorbit
import pyupbit
import time

ORDER_ELAPSED_LIMIT = 4             # 4초후 미체결 주문 취소

with open("korbit.key") as f:
    lines = f.readlines()
    key = lines[0].strip()
    secret = lines[1].strip()
korbit = pykorbit.Korbit(key, secret)

with open("upbit.key") as f:
    lines = f.readlines()
    access = lines[0].strip()
    secret = lines[1].strip()
upbit = pyupbit.Upbit(access, secret)


class BalanceWorker(QThread):
    """거래소의 잔고를 조회하는 스레드 클래스
    """
    finished = pyqtSignal(dict)

    def run(self):
        while True:
            try:
                balances = korbit.get_balances()
                krw = balances['krw']
                xrp = balances['xrp']

                upbit_krw = upbit.get_balance(ticker="KRW", verbose=True)
                upbit_xrp = upbit.get_balance(ticker="XRP", verbose=True)

                data = {
                    'korbit': [krw, xrp],
                    'upbit': [upbit_krw, upbit_xrp]
                }
                self.finished.emit(data)
            except:
                pass
            time.sleep(2)


class OrderWorker(QThread):
    send_msg = pyqtSignal(str)

    def __init__(self, main):
        super().__init__()
        self.main = main

    def run(self):
        while True:
            if self.main.korbit_started and self.main.upbit_started and self.main.balance_started:
                self.order()
            time.sleep(0.2)

    def order(self):
        # 코빗이 싼 경우
        # 코빗의 지정가 매수가격(매수 1호가+0.1) < 업비트의 시장가 매도가격(매수 1호가)
        korbit_buy_hoga = self.main.korbit_bid0_price + 0.1
        upbit_sell_hoga = self.main.upbit_bid0_price
        korbit_trading_fee = korbit_buy_hoga * 0.2 * 0.01
        upbit_trading_fee = upbit_sell_hoga * 0.05 * 0.01

        # 코빗 지정가 매수 금액이 매수 1호가랑 같지 않아야 함 (시장가로 체결되기 때문)
        if (korbit_buy_hoga < upbit_sell_hoga and
            korbit_buy_hoga != self.main.korbit_ask0_price):
            quantity = 20
            #profit = upbit_sell_hoga - korbit_buy_hoga - upbit_trading_fee - korbit_trading_fee
            profit = upbit_sell_hoga - korbit_buy_hoga - upbit_trading_fee

            if (self.main.running and profit >= self.main.min_profit and
                self.main.upbit_xrp_balance >= quantity and
                self.main.korbit_krw_balance > (korbit_buy_hoga * quantity)):

                # 코빗은 지정가 매수
                try:
                    resp = korbit.buy_limit_order("XRP", korbit_buy_hoga, quantity)

                    # 코빗 체결 대기 또는 취소
                    order_id, order_status, _ = resp
                    if order_status == 'success':
                        order_ret = self.wait_korbit_close_order(order_id)

                        # 주문 취소시 현재 세션 종료
                        if order_ret == 1:
                            return
                    else:
                        return
                except:
                    return

                # 업비트는 시장가 매도
                upbit.sell_market_order("KRW-XRP", quantity)
                text = f"(실매매) 코빗 지정가 매수 {korbit_buy_hoga:.1f} | 업비트 시장가 매도 {self.main.upbit_bid0_price:.1f} | 차익 {profit:.1f}"
            else:
                text = f"코빗 지정가 매수 {korbit_buy_hoga:.1f} | 업비트 시장가 매도 {self.main.upbit_bid0_price:.1f} | 차익 {profit:.1f}"
            self.send_msg.emit(text)

        # 업비트가 싼 경우
        # 업비트의 시장가 매수가격(매도 1호가) < 코빗의 지정가 매도가격(매도 1호가-0.1)
        korbit_sell_hoga = self.main.korbit_ask0_price - 0.1
        upbit_buy_hoga = self.main.upbit_ask0_price
        korbit_trading_fee = korbit_sell_hoga * 0.2 * 0.01
        upbit_trading_fee = upbit_buy_hoga * 0.05 * 0.01

        # 코빗 지정가 매도 금액이 매수 1호가랑 같지 않아야 함 (시장가로 체결되기 때문)
        if (upbit_buy_hoga < korbit_sell_hoga and
            korbit_sell_hoga != self.main.korbit_bid0_price):
            quantity = 20
            #profit = korbit_sell_hoga - upbit_buy_hoga - upbit_trading_fee - korbit_trading_fee
            profit = korbit_sell_hoga - upbit_buy_hoga - upbit_trading_fee

            if (self.main.running and profit >= self.main.min_profit and
                self.main.korbit_xrp_balance >= quantity and
                self.main.upbit_krw_balance > (upbit_buy_hoga * quantity * 1.01)):

                # 코빗은 지정가 매도
                try:
                    resp = korbit.sell_limit_order("XRP", korbit_buy_hoga, quantity)

                    # 코빗 체결 대기 또는 취소
                    order_id, order_status, _ = resp
                    if order_status == 'success':
                        order_ret = self.wait_korbit_close_order(order_id)

                        # 주문 취소시 현재 세션 종료
                        if order_ret == 1:
                            return
                    else:
                        return
                except:
                    return

                # 업비트는 시장가 매수
                upbit.buy_market_order("KRW-XRP", quantity)
                text = f"(실매매) 코빗 지정가 매도 {korbit_buy_hoga:.1f} | 업비트 시장가 매수 {self.main.upbit_bid0_price:.1f} | 차익 {profit:.1f}"
            else:
                text = f"코빗 지정가 매도 {korbit_buy_hoga:.1f} | 업비트 시장가 매수 {self.main.upbit_bid0_price:.1f} | 차익 {profit:.1f}"

            self.send_msg.emit(text)

    def wait_korbit_close_order(self, order_id):
        try:
            start_time = time.time()
            while len(korbit.get_open_orders("XRP")):
                time.sleep(0.5)
                end_time = time.time()
                elapsed_time = end_time - start_time

                if (elapsed_time > ORDER_ELAPSED_LIMIT):
                    korbit.cancel_order("XRP", order_id)
                    return 1

                self.send_msg.emit("(실매매) 코빗 체결 대기 중 ...")
            return 0
        except:
            pass


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
        self.setGeometry(200, 200, 650, 800)
        self.setWindowTitle("Arbitrage Bot v1.0")

        self.running = False
        self.korbit_started = False
        self.upbit_started = False
        self.balance_started = False
        self.min_profit = 4

        self.korbit_xrp_balance = 0
        self.korbit_krw_balance = 0
        self.upbit_xrp_balance = 0
        self.upbit_krw_balance = 0

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
        layout = QGridLayout(widget)
        layout.setSpacing(10)

        self.add_table_widget()
        self.create_ws_threads()
        self.create_threads()

        label1 = QLabel("코빗 (Maker: -0.05%, Taker: 0.20%)")
        label2 = QLabel("업비트 (Maker: 0.05%, Taker: 0.05%)")

        self.plain_text = QPlainTextEdit()

        self.btn_start = QPushButton("재정거래 시작")
        self.btn_start.clicked.connect(self.btn_start_clicked)
        self.btn_stop = QPushButton("재정거래 정지")
        self.btn_stop.clicked.connect(self.btn_stop_clicked)

        hbox = QHBoxLayout()
        label = QLabel("최소 차익 ")
        self.lineedit = QLineEdit(str(self.min_profit))
        apply_btn = QPushButton("적용하기")
        apply_btn.clicked.connect(self.update_min_profit)
        hbox.addWidget(label)
        hbox.addWidget(self.lineedit)
        hbox.addWidget(apply_btn)

        layout.addLayout(hbox, 0, 0)
        layout.addWidget(label1, 1, 0)
        layout.addWidget(label2, 1, 1)
        layout.addWidget(self.tw_korbit, 2, 0)
        layout.addWidget(self.tw_upbit , 2, 1)
        layout.addWidget(self.table_widget1, 3, 0)
        layout.addWidget(self.table_widget2, 3, 1)
        layout.addWidget(self.plain_text, 4, 0, 1, 2)
        layout.addWidget(self.btn_start, 5, 0)
        layout.addWidget(self.btn_stop, 5, 1)

        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 0)
        layout.setRowStretch(2, 1)
        layout.setRowStretch(3, 3)
        layout.setRowStretch(4, 2)
        layout.setRowStretch(5, 1)

        self.setCentralWidget(widget)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def update_min_profit(self):
        price = float(self.lineedit.text())
        self.min_profit = price
        self.plain_text.appendPlainText(f"최소 차익이 {price} 원이 적용되었습니다.")

    def create_threads(self):
        self.balance_worker = BalanceWorker()
        self.balance_worker.finished.connect(self.update_balance)
        self.balance_worker.start()

        self.order_worker = OrderWorker(self)
        self.order_worker.send_msg.connect(self.update_plaintext)
        self.order_worker.start()

    @pyqtSlot(str)
    def update_plaintext(self, text):
        self.plain_text.appendPlainText(text)

    @pyqtSlot(dict)
    def update_balance(self, data):
        # korbit
        korbit_balance = data.get('korbit')
        krw_availalbe = korbit_balance[0]['available']
        xrp_availalbe = korbit_balance[1]['available']

        self.korbit_krw_balance = float(krw_availalbe)
        self.korbit_xrp_balance = float(xrp_availalbe)

        item = QTableWidgetItem("KRW")
        item.setTextAlignment(int(Qt.AlignCenter|Qt.AlignVCenter))
        self.tw_korbit.setItem(0, 0, item)

        item = QTableWidgetItem(krw_availalbe)
        item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
        self.tw_korbit.setItem(0, 1, item)

        item = QTableWidgetItem("XRP")
        item.setTextAlignment(int(Qt.AlignCenter|Qt.AlignVCenter))
        self.tw_korbit.setItem(1, 0, item)

        item = QTableWidgetItem(xrp_availalbe)
        item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
        self.tw_korbit.setItem(1, 1, item)

        upbit_balance = data.get('upbit')
        krw_availalbe = upbit_balance[0]['balance']
        xrp_availalbe = upbit_balance[1]['balance']
        self.upbit_krw_balance = float(krw_availalbe)
        self.upbit_xrp_balance = float(xrp_availalbe)

        self.balance_started = True

        item = QTableWidgetItem("KRW")
        item.setTextAlignment(int(Qt.AlignCenter|Qt.AlignVCenter))
        self.tw_upbit.setItem(0, 0, item)

        item = QTableWidgetItem(krw_availalbe)
        item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
        self.tw_upbit.setItem(0, 1, item)

        item = QTableWidgetItem("XRP")
        item.setTextAlignment(int(Qt.AlignCenter|Qt.AlignVCenter))
        self.tw_upbit.setItem(1, 0, item)

        item = QTableWidgetItem(xrp_availalbe)
        item.setTextAlignment(int(Qt.AlignRight|Qt.AlignVCenter))
        self.tw_upbit.setItem(1, 1, item)

    def btn_start_clicked(self):
        self.running = True
        self.status_bar.showMessage("상태: 재정거래 중")

    def btn_stop_clicked(self):
        self.running = False
        self.status_bar.showMessage("상태: 감시 중")

    def add_table_widget(self):
        labels = ["보유자산", "보유수량"]
        # korbit
        self.tw_korbit = QTableWidget(self)
        self.tw_korbit.setColumnCount(2)
        self.tw_korbit.setColumnWidth(0, 100)
        self.tw_korbit.setColumnWidth(1, 200)
        self.tw_korbit.setRowCount(2)
        self.tw_korbit.verticalHeader().setVisible(False)
        self.tw_korbit.setHorizontalHeaderLabels(labels)

        self.table_widget1 = QTableWidget(self)
        self.table_widget1.setColumnCount(3)
        self.table_widget1.setRowCount(10)
        self.table_widget1.verticalHeader().setVisible(False)
        self.table_widget1.horizontalHeader().setVisible(False)

        # upbit
        self.tw_upbit = QTableWidget(self)
        self.tw_upbit.setColumnCount(2)
        self.tw_upbit.setColumnWidth(0, 100)
        self.tw_upbit.setColumnWidth(1, 200)
        self.tw_upbit.setRowCount(2)
        self.tw_upbit.verticalHeader().setVisible(False)
        self.tw_upbit.setHorizontalHeaderLabels(labels)

        self.table_widget2 = QTableWidget(self)
        self.table_widget2.setColumnCount(3)
        self.table_widget2.setRowCount(10)
        self.table_widget2.verticalHeader().setVisible(False)
        self.table_widget2.horizontalHeader().setVisible(False)

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

            self.upbit_started = True

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