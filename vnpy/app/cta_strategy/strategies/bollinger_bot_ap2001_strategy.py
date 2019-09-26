# encoding: UTF-8

"""
基于布林通道的双边交易策略
"""

from vnpy.app.cta_strategy import (
    CtaTemplate,
    BarGenerator,
    ArrayManager,
    BarData,
    TickData
)


class BollingerBotAP001Strategy(CtaTemplate):
    """基于布林通道的交易策略"""
    author = u'tonywang_efun'

    # 策略参数
    initDays = 10  # 初始化数据所用的天数
    fixedSize = 1  # 每次交易的数量

    # （多头参数）
    fixWinPrcnt = 2.4   # 固定止盈百分比
    bollLength = 58  # 通道窗口数
    entryDev = 2.6  # 开仓偏差
    exitDev = 1.2  # 平仓偏差
    trailingPrcnt = 1.0  # 移动止损百分比
    maLength = 12  # 过滤用均线窗口

    # （空头参数）
    shortfixWinPrcnt = 2.9   # 固定止盈百分比
    shortBollLength = 26  # 通道窗口数
    shortEntryDev = 2.4  # 开仓偏差
    shortExitDev = 0.8  # 平仓偏差
    shortTrailingPrcnt = 1.2  # 移动止损百分比
    shortMaLength = 60  # 过滤用均线窗口


    # 公共策略变量
    posPrice = 0    # 持仓价

    # 策略变量(多头)
    entryLine = 0  # 开仓上轨
    exitLine = 0  # 平仓上轨
    maFilter = 0  # 均线过滤
    maFilterPrevious = 0  # 上一期均线
    intraTradeHigh = 0  # 持仓期内的最高点
    longEntry = 0  # 多头开仓
    longExit = 0  # 多头平仓

    # 策略变量(空头)
    shortEntryLine = 0  # 开仓上轨
    shortExitLine = 0  # 平仓上轨
    shortMaFilter = 0  # 均线过滤
    shortMaFilterPrevious = 0  # 上一期均线
    intraTradeLow = 0  # 持仓期内的最最低点
    shortEntry = 0  # 空头开仓
    shortExit = 0  # 空头平仓

    # 参数列表，保存了参数的名称
    parameters = ['initDays',
                  'fixedSize',
                  'fixWinPrcnt',
                  'shortfixWinPrcnt',
                  'bollLength',
                  'entryDev',
                  'exitDev',
                  'trailingPrcnt',
                  'maLength',
                  'shortBollLength',
                  'shortEntryDev',
                  'shortExitDev',
                  'shortTrailingPrcnt',
                  'shortMaLength']

    # 变量列表，保存了变量的名称
    variables = ['posPrice',
                 'entryLine',
                 'exitLine',
                 'shortEntryLine',
                 'shortExitLine',
                 'intraTradeHigh',
                 'intraTradeLow',
                 'longEntry',
                 'longExit',
                 'shortEntry',
                 'shortExit']

    # ----------------------------------------------------------------------
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super(BollingerBotAP001Strategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.bg = BarGenerator(self.on_bar, 6, self.on_xmin_bar)
        self.am = ArrayManager(100)

    # ----------------------------------------------------------------------
    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(self.initDays)

    # ----------------------------------------------------------------------
    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")
        self.put_event()

    # ----------------------------------------------------------------------
    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")
        self.put_event()

    # ----------------------------------------------------------------------
    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg.update_tick(tick)

    # ----------------------------------------------------------------------
    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.bg.update_bar(bar)

    def on_xmin_bar(self, bar: BarData):
        """收到x分钟K线"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        self.cancel_all()

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        # 计算多头指标数值
        self.entryLine, self.exitLine = am.boll_double_up(self.bollLength, self.entryDev, self.exitDev)
        ma_array = am.sma(self.maLength, True)
        self.maFilter = ma_array[-1]
        self.maFilterPrevious = ma_array[-2]

        # 计算空头指标数值
        self.shortEntryLine, self.shortExitLine = am.boll_double_down(self.shortBollLength, self.shortEntryDev,
                                                                      self.shortExitDev)
        short_ma_array = am.sma(self.shortMaLength, True)
        self.shortMaFilter = short_ma_array[-1]
        self.shortMaFilterPrevious = short_ma_array[-2]

        # 当前无仓位，发送OCO开仓委托
        if self.pos == 0:
            self.intraTradeHigh = bar.high_price
            self.intraTradeLow = bar.low_price

            if bar.close_price > self.maFilter > self.maFilterPrevious:
                self.longEntry = self.entryLine
                self.buy(self.longEntry, self.fixedSize, True)
            elif bar.close_price < self.shortMaFilter < self.shortMaFilterPrevious:
                self.shortEntry = self.shortEntryLine
                self.short(self.shortEntry, self.fixedSize, True)

        # 持有多头仓位
        elif self.pos > 0:
            if 0 < self.posPrice < bar.close_price \
                    and (bar.close_price - self.posPrice) / self.posPrice > (self.fixWinPrcnt / 100):
                print("fix percent sell-------------------------------")
                self.sell(bar.close_price * 0.99, abs(self.pos))
            else:
                self.intraTradeHigh = max(self.intraTradeHigh, bar.high_price)
                self.longExit = self.intraTradeHigh * (1 - self.trailingPrcnt / 100)
                self.longExit = min(self.longExit, self.exitLine)

                self.sell(self.longExit, abs(self.pos), True)

        # 持有空头仓位
        elif self.pos < 0:
            if bar.close_price < self.posPrice \
                    and (self.posPrice - bar.close_price) / self.posPrice > (self.shortfixWinPrcnt / 100):
                print("fix percent cover-------------------------------")
                self.cover(bar.close_price * 1.01, abs(self.pos))
            else:
                self.intraTradeLow = min(self.intraTradeLow, bar.low_price)
                self.shortExit = self.intraTradeLow * (1 + self.shortTrailingPrcnt / 100)
                self.shortExit = max(self.shortExit, self.shortExitLine)

                self.cover(self.shortExit, abs(self.pos), True)

        # 发出状态更新事件
        self.put_event()

    def on_order(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def on_trade(self, trade):
        # 发出状态更新事件

        print(trade)
        self.send_email(str(trade))
        self.posPrice = trade.price
        self.put_event()

    # ----------------------------------------------------------------------
    def on_stop_order(self, so):
        """停止单推送"""
        pass