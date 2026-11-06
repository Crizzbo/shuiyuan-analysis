"""合成算术演示，非金融估值模型；无网络和项目外数据。"""
def scenario(price, factor):
    return price * factor

def crosscheck(price, factor):
    return price + price * (factor - 1)
