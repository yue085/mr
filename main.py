import json
import sys
import time
from copy import deepcopy
from pathlib import Path

from httpx import Client

curFileDir = Path(sys.argv[0]).parent  # 当前文件路径

try:
    with open(curFileDir / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except:
    print("载入配置文件出错")
    exit(0)

cookies: dict = config["cookies"]
headers: dict = config["headers"]
sleep_time: int = config["sleep_time"]
task_configs: dict = config["task_configs"]


class Huya:
    def __init__(self, cookie):
        # self.cookie = cookie
        self.headers = deepcopy(headers["huya"])
        self.headers["cookie"] = cookie
        self.client = Client(headers=self.headers)
        self.daily_actId = task_configs["huya"]["daily_actId"]
        self.flag_task_id = task_configs["huya"]["flag_task_id"]
        self.id_map = task_configs["huya"]["id_map"]
        # ----------------------------------------------

    def get_daily_task_status(self):
        """
        获取任务完成的状态
        :param client:httpxClient
        :return:
        """
        url = "https://activityapi.huya.com/acttask/getActUserTaskDetail"
        params = {
            "callback": "getUserTasks_matchComponent8",
            "actId": self.daily_actId,
            "platform": 1,
            "_": int(time.time() * 1000),
        }
        try:
            rep = self.client.get(url, params=params)
            # print(rep.text)
            res = json.loads(rep.text[29:-1])
        except Exception as e:
            print(f"请求错误:\r\n{e}")
            return
        if res.get("status") == 200:
            return res.get("data")

    def get_daily_prize(self, task_id: int):
        url = "https://activityapi.huya.com/acttask/receivePrize"
        params = {
            "callback": "getTaskAward_matchComponent8",
            "taskId": task_id,
            "actId": self.daily_actId,
            "platform": 1,
            "_": int(time.time() * 1000),
        }
        try:
            rep = self.client.get(url, params=params)
            # print(rep.text)
            res = json.loads(rep.text[29:-1])
        except Exception as e:
            print(f"请求错误:\r\n{e}")
            return
        if res.get("status") == 200:
            # print(res)
            print(f"{'》' * 10}领取成功:{self.id_map[str(task_id)]}")
        else:
            print(f"{'》' * 10}领取失败:{self.id_map[str(task_id)]}\r\n{res}")

    def main(self):

        while True:
            done_tasks = []  # 已完成但未领取
            not_done_tasks = []  # 未完成的任务
            prizes_exist = []  # 已领取的
            daily_tasks_info = self.get_daily_task_status()
            for task in daily_tasks_info:
                if task["taskId"] in prizes_exist:  # 跳过完成的任务
                    continue
                if task["taskStatus"] == 1 and task["prizeStatus"] == 1:  # 已领取过
                    prizes_exist.append(task["taskId"])
                elif task["taskStatus"] == 1 and task["prizeStatus"] == 0:  # 已完成但没有领取
                    done_tasks.append(task["taskId"])
                else:
                    not_done_tasks.append(task["taskId"])
            print(f"已领取的任务:{[self.id_map[str(tid)] for tid in prizes_exist]}")
            print(f"已完成的任务:{[self.id_map[str(tid)] for tid in done_tasks]}")
            print(f"未完成的任务:{[self.id_map[str(tid)] for tid in not_done_tasks]}")
            for taskid in done_tasks:
                self.get_daily_prize(taskid)
            if self.flag_task_id in prizes_exist:  # 如果所有任务都完成了
                break
            time.sleep(sleep_time)


class Bili:
    def __init__(self, cookie: str):
        self.headers = deepcopy(headers["bili"])
        # self.headers["cookie"] = cookie
        # noinspection PyTypeChecker
        self.cookies = dict([_.split("=", 1) for _ in cookie.split("; ")])
        self.client = Client(headers=self.headers, cookies=self.cookies)
        self.id_map: dict = task_configs["bili"]["id_map"]
        self.csrf = self.cookies["bili_jct"]
        # ---------------------------------------
        self.done_tasks = []  # 已完成的任务

    def get_reward(self, data, reward_name):
        """
        领取奖励
        :param client:
        :param data: post的data
        :param reward_name: 奖励的名字
        :return: None
        """
        url = "https://api.bilibili.com/x/activity/mission/task/reward/receive"
        try:
            rep = self.client.post(url, data=data)
            res = rep.json()
        except:
            print("请求错误")
            return
        # print(f"res: {res}")
        if res["code"] == 0:
            print(f"{'》' * 10}[[领取成功]]{reward_name} : 领取成功{'《' * 10}")
        else:
            print(
                f'{"》" * 10}[[领取失败]]{reward_name}: {res["code"]}--{res["message"]}{"《" * 10}'
            )

    def get_reward_info(self, taskid):
        """
        获取奖励的参数
        :param taskid:
        :return: 返回None的话就是不能领取的奖励
        """
        # print(taskid)
        url = "https://api.bilibili.com/x/activity/mission/single_task"
        params = {"csrf": self.csrf, "id": taskid}
        try:
            response = self.client.get(url, params=params)
            res = response.json()
        except:
            print("请求错误")
            return None
        # print(res)
        if res["code"] != 0:
            print("状态码错误")
            return None
        reward_info = f'[{res["data"]["task_info"]["reward_info"]["reward_name"]}]  >>>剩余数量:[{res["data"]["task_info"]["reward_period_stock_num"]}]<<<'
        if res["data"]["task_info"]["receive_status"] == 3:
            print(f"已领取过: {reward_info}")
            self.done_tasks.append(
                res["data"]["task_info"]["reward_info"]["reward_name"]
            )
            return
        elif res["data"]["task_info"]["reward_period_stock_num"] == 0:
            print(f"已领完: {reward_info}")
            self.done_tasks.append(
                res["data"]["task_info"]["reward_info"]["reward_name"]
            )
            return
        elif res["data"]["task_info"]["receive_status"] == 0:
            print(f"无法领取: {reward_info}")
            return
        print(f"尝试领取: {reward_info}")
        rewardData = {
            "csrf": self.csrf,
            "act_id": res["data"]["task_info"]["group_list"][0]["act_id"],
            "task_id": res["data"]["task_info"]["group_list"][0]["task_id"],
            "group_id": res["data"]["task_info"]["group_list"][0]["group_id"],
            "receive_id": res["data"]["task_info"]["receive_id"],
            "receive_from": "missionLandingPage",
        }
        rewardName = res["data"]["task_info"]["reward_info"]["reward_name"]
        return rewardData, rewardName
        # self.get_reward(rewardData, rewardName)

    def main(self):
        while True:
            self.done_tasks.clear()
            for task_id in self.id_map.keys():
                if info := self.get_reward_info(task_id):
                    self.get_reward(info[0], info[1])
            if len(self.done_tasks) == len(self.id_map.keys()):
                break
            time.sleep(sleep_time)


class Douyu:
    def __init__(self, cookie):
        self.headers = deepcopy(headers["douyu"])
        self.headers["cookie"] = cookie
        self.client = Client(headers=self.headers)
        self.id_map: dict = task_configs["douyu"]["id_map"]

    def get_task_prize(self, task_id):
        url = "https://www.douyu.com/japi/carnival/nc/roomTask/getPrize"
        data = {"taskId": task_id}
        try:
            rep = self.client.post(url, data=data)
            res = rep.json()
        except:
            print("请求错误")
            return
        if res["error"] == 0:
            print(f"领取成功: [{self.id_map[task_id]}]")
            return True
        elif res["error"] == 2002:
            print(f"已领取过: [{self.id_map[task_id]}]")
            return True
        else:
            print(res)

    def main(self):
        while True:
            done_tasks = []
            for task_id in self.id_map.keys():
                if self.get_task_prize(task_id):
                    done_tasks.append(task_id)
            if len(done_tasks) == len(self.id_map.keys()):
                break
            time.sleep(sleep_time)


if __name__ == "__main__":
    while True:
        print("huya")
        for hy_ck in cookies["huya"]:
            Huya(hy_ck).main()
            print("-" * 30)
        print("#" * 30)
        print("bili")
        for bili_ck in cookies["bili"]:
            Bili(bili_ck).main()
            print("-" * 30)
        print("#" * 30)
        print("douyu")
        for dy_ck in cookies["douyu"]:
            Douyu(dy_ck).main()
            print("-" * 30)
        print("#" * 50)
        print("*" * 50)
        print("#" * 50)
        time.sleep(sleep_time)
