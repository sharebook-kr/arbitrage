# arbitrage
upbit-korbit arbitrage bot

![arb03](https://user-images.githubusercontent.com/23475470/168280823-829fe518-7654-4629-8d00-f3a4e7d8974c.gif)

# 실행하는 방법

main.py가 있는 디렉토리에 korbit.key 파일과 upbit.key 파일을 생성합니다. 각 파일의 첫 번째 줄과 두 번째 줄에 발급 받은 API의 key(access)와 secret을 넣어줍니다. 

```
$ pip install pykorbit
$ pip install pyupbit
$ pip install pyqt5
$ python main.py
```

# 초기 설정하는법

업비트에 리플 1500개 이상, 코빗에도 리플 1500개 이상을 보유한 상태와 충분한 원화 잔고
바이낸스에는 리플 3000개를 1배 공매도 (short)을 통해서 리플 가격 하락에 대한 헤지(hedge)
