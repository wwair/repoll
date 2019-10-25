
from .models import models
from polls.models import *
import redis
from django.dispatch import receiver
from django.core.signals import request_finished
from django.forms.models import model_to_dict
from django.http import HttpResponse
import time
# 针对model 的signal
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save

# 定义一个信号
import django.dispatch
work_done = django.dispatch.Signal(providing_args=['redis_text', 'request'])


# def create_signal(request, redis_text):
#     print("我已经做完了工作。现在我发送一个信号出去，给那些指定的接收器。")
#
#     # 发送信号，将请求的url地址和时间一并传递过去
#     work_done.send(create_signal, request=request, redis_text=redis_text)
#     return HttpResponse("200,ok")
#
#
# @receiver(post_save, sender=ApplyRedisText, dispatch_uid="mymodel_post_save")
# def model_per_saved(sender, **kwargs):
#     redis_text = kwargs['instance'].apply_text
#     work_done.send(create_signal, redis_text=redis_text)
#
#
# @receiver(work_done, sender=create_signal)
# def my_callback(sender, **kwargs):
#     print("我在%s时间收到来自%s的信号" % (kwargs['redis_text'], sender))


@receiver(post_save, sender=ApplyRedisText, dispatch_uid="mymodel_post_save")
def my_model_handler(sender, **kwargs):
    redis_ip = ''
    redis_port = ''
    redis_apply_ip = Ipaddr.objects.all()
    redis_ins_id = kwargs['instance'].redis_ins_id
    redis_ins_obj = RedisIns.objects.filter(id=redis_ins_id)
    all_redis_ip = [redis_ip_ipaddr.__dict__['ip'] for redis_ip_ipaddr in redis_apply_ip]
    redis_text = kwargs['instance'].apply_text
    if isinstance(redis_text, str):
        try:
            redis_text_split = redis_text.split(":")
            redis_ip = redis_text_split[0]
            redis_port = redis_text_split[1]
            redis_mem = redis_text_split[2]
            if redis_ip in all_redis_ip:
                print("{0}在Redis云管列表中...".format(redis_ip))
        except ValueError as e:
            print(e)

    redis_ins_obj_type = redis_ins_obj.values('redis_type').first()
    redis_ins_obj_name = redis_ins_obj.values('redis_ins_name').first()
    redis_ins_obj_mem = redis_ins_obj.values('redis_mem').first()
    redis_ins_type = RedisIns.type_choice[redis_ins_obj_type['redis_type']][1]
    # print(redis_ins_obj_name, redis_ins_type)
    # print('Saved: {}'.format(kwargs['instance'].__dict__))
    a = RedisStandalone(redis_ins=redis_ins_obj,
                        redis_ins_name=redis_ins_obj_name,
                        redis_ins_type=redis_ins_type,
                        redis_ins_mem=redis_ins_obj_mem,
                        redis_ip=redis_ip,
                        redis_port=redis_port)
    a.standalone_conf()
    while True:
        for i in a.saved_redis_qps():
            print(i)
        time.sleep(1)


def get_redis_conf(redis_type):
    """
    通过redis的模式获取当前所有的配置文件
    :param redis_type:
    :return:
    """
    obj = RedisConf.objects.all().filter(redis_type=redis_type)
    return obj


class RedisStandalone:

    def __init__(self, redis_ins, redis_ins_name, redis_ins_type, redis_ins_mem, redis_ip, redis_port):
        self.redis_ins_ip = [r.__dict__ for r in redis_ins]
        self.redis_ins_name = redis_ins_name
        self.redis_ins_type = redis_ins_type
        self.redis_ins_mem = redis_ins_mem
        self.redis_ip = redis_ip
        self.redis_port = redis_port

    def standalone_conf(self):
        redis_conf = get_redis_conf(redis_type="Redis-Standalone")
        print(self.redis_ins_name)
        print(self.redis_ins_type)
        print(redis_conf)

    def saved_redis_running_ins(self):
        obj = RedisRunningIns(running_ins_name=self.redis_ins_name,
                              redis_type=self.redis_ins_type,
                              device_mem=self.redis_ins_mem)
        obj.save()
        return True

    def saved_redis_qps(self):
        # print("1==={0}===".format(self.redis_ins_ip))
        # print("2==={0}===".format(self.redis_ip))
        count = 0
        for i in range(0, count+1):
            r = RedisWatch(redis_ins_ip=self.redis_ip, redis_ins_port=self.redis_port)
            time.sleep(1)
            count += 1
            yield r.get_redis_ins_qps()
        # r = RedisWatch(redis_ins_ip=self.redis_ip, redis_ins_port=self.redis_port)
        # return r.get_redis_ins_qps()


class RedisWatch:

    def __init__(self, redis_ins_ip, redis_ins_port):
        self.redis_ins_ip = redis_ins_ip
        self.redis_pyhon_ins = redis.ConnectionPool(host="127.0.0.1", port=redis_ins_port)
        self.redis_pool = redis.Redis(connection_pool=self.redis_pyhon_ins)

    def get_redis_ins_qps(self):
        qps = self.redis_pool.info()
        return qps['instantaneous_ops_per_sec']


# @receiver(request_finished)
# def my_callback(sender, **kwargs):
#     print("Request finished!")
#
#
# @receiver(pre_save, sender=RedisIns)
# def my_handler(sender, **kwargs):
#     print("Hello World!!!")

# def log(log_type, msg=None, asset=None, new_asset=None, request=None):
#     """
#     记录日志
#     """
#     event = models.EventLog()
#     if log_type == "upline":
#         event.name = "%s <%s> ：  上线" % (asset.name, asset.sn)
#         event.asset = asset
#         event.detail = "资产成功上线！"
#         event.user = request.user
#     elif log_type == "approve_failed":
#         event.name = "%s <%s> ：  审批失败" % (new_asset.asset_type, new_asset.sn)
#         event.new_asset = new_asset
#         event.detail = "审批失败！\n%s" % msg
#         event.user = request.user
#     # 更多日志类型.....
#     event.save()


class ApproveRedis:
    """
    审批资产并上线。
    """
    def __init__(self, request, asset_id):
        self.request = request
        self.asset_id = asset_id
        self.new_asset = RedisApply.objects.get(id=asset_id)
        # self.data = json.loads(self.new_asset.data)

    # def asset_upline(self):
    #     # 为以后的其它类型资产扩展留下接口
    #     func = getattr(self, "asset_upline")
    #     ret = func()
    #     return ret

    def _server_upline(self):
        # 在实际的生产环境中，下面的操作应该是原子性的整体事务，任何一步出现异常，所有操作都要回滚。
        asset = self.create_asset()  # 创建一条资产并返回资产对象。注意要和待审批区的资产区分开。
        print(asset)
        return True

    def create_asset(self):
        """
        创建Redis实例并上线
        :return:
        """
        # 利用request.user自动获取当前管理人员的信息，作为审批人添加到Redis实例数据中。
        try:
            if not RedisIns.objects.filter(redis_ins_name=self.new_asset.apply_ins_name):
                asset = RedisIns.objects.create(redis_ins_name=self.new_asset.apply_ins_name,
                                                ins_disc=self.new_asset.ins_disc,
                                                redis_type=self.new_asset.redis_type,
                                                redis_mem=self.new_asset.redis_mem,
                                                sys_author=self.new_asset.sys_author,
                                                area=self.new_asset.area,
                                                pub_date=self.new_asset.pub_date,
                                                approval_user=self.request.user,
                                                ins_status=RedisIns.ins_choice[3][0]
                                                )
            else:
                return False
        except ValueError as e:
            return e
        return asset

    def deny_create(self):
        """

        :return:
        """
        try:
            if not RedisIns.objects.filter(redis_ins_name=self.new_asset.apply_ins_name):
                asset = RedisIns.objects.create(redis_ins_name=self.new_asset.apply_ins_name,
                                                ins_disc=self.new_asset.ins_disc,
                                                redis_type=self.new_asset.redis_type,
                                                redis_mem=self.new_asset.redis_mem,
                                                sys_author=self.new_asset.sys_author,
                                                area=self.new_asset.area,
                                                pub_date=self.new_asset.pub_date,
                                                approval_user=self.request.user,
                                                ins_status=RedisIns.ins_choice[3][0]
                                                )
                if RedisIns.objects.filter(redis_ins_name=self.new_asset.apply_ins_name).values('ins_status') == 0:
                    RedisApply.objects.filter(redis_ins_name=self.new_asset.apply_ins_name).update(
                        apply_status=RedisApply.status_choice[2][0]
                    )
            else:
                RedisIns.objects.filter(redis_ins_name=self.new_asset.apply_ins_name).update(ins_status=RedisIns.ins_choice[3][0])
                RedisApply.objects.filter(redis_ins_name=self.new_asset.apply_ins_name).update(
                    apply_status=RedisApply.status_choice[2][0]
                )
                return True
        except ValueError as e:
            return e
        return asset

    def redis_apply_status_update(self):
        RedisApply.objects.filter(id=self.asset_id).update(apply_status=1)
        # obj.save()
        return True







