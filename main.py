# discord.py
import configparser
import csv
import datetime
import os

import discord
from discord.ext import commands

# タイムゾーン (日付は朝9時に変更=UTC)
timezone_date = datetime.timezone(datetime.timedelta(hours=0))
timezone = datetime.timezone(datetime.timedelta(hours=9))

# 起動
print('起動しました')

# コンフィグ
config = configparser.ConfigParser()
config.read('config.ini', encoding='UTF-8')

ss_guild = int(config['SESSION']['GUILD'])
ss_channel = int(config['SESSION']['CHANNEL'])
ss_owner = int(config['SESSION']['OWNER'])

# 起動
print(f"設定を読み込みました: guild={ss_guild}, channel={ss_channel}, owner={ss_owner}")

# フォルダ
os.makedirs('./data', exist_ok=True)
os.makedirs('./data/log', exist_ok=True)
os.makedirs('./data/corrupted', exist_ok=True)

# 起動
print('フォルダを生成しました')


# セッション
class Session:
    def __init__(self, channel, owner):
        self.channel = channel
        self.owner = owner
        self.path = None
        self.enabled = False

    def is_target(self, channel):
        return channel is not None and channel.id == self.channel


# セッション
session = Session(ss_channel, ss_owner)
session.path = f'./data/corrupted/{datetime.datetime.now(timezone_date).date()}.csv'

# 接続に必要なオブジェクトを生成
bot = commands.Bot(command_prefix='/')


# 起動時に動作する処理
@bot.event
async def on_ready():
    # 起動したらターミナルにログイン通知が表示される

    guild = bot.get_guild(ss_guild)
    if guild is None:
        print('サーバーが見つかりません')
        return
    channel = guild.get_channel(ss_channel)
    if channel is None:
        print('チャンネルが見つかりません')
        return
    member = guild.get_member(ss_owner)
    if member is None:
        print('監視対象が見つかりません')
        return
    if ss_owner in channel.members:
        await on_voice_state_update(
            member,
            discord.VoiceState(data={}, channel=None),
            discord.VoiceState(data={}, channel=channel),
        )
    print('ログインしました')


# ログ
class Log:
    def __init__(self, path):
        self.path = path
        self.fd = None
        self.writer = None

    def __enter__(self):
        is_new = os.path.exists(self.path)
        self.fd = open(self.path, 'a', newline='', encoding='UTF-8')
        self.writer = csv.writer(self.fd)
        if not is_new:
            self.writer.writerow(['種類', '時間', 'Discord ID', 'Discord 名前'])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fd.close()

    def log(self, time, uid, fullname, joined):
        self.writer.writerow(['参加' if joined else '退出', time, uid, fullname])


# VCのメンバー移動時の処理
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # 移動していない
    if before.channel == after.channel:
        return

    # 関係ないチャンネル
    if not session.is_target(before.channel) and not session.is_target(after.channel):
        return

    # 主
    if member.id == session.owner:
        # 参加
        if session.is_target(after.channel):
            now = datetime.datetime.now(timezone)

            session.enabled = True
            session.path = f'./data/log/{datetime.datetime.now(timezone_date).date()}.csv'

            # 主
            with Log(session.path) as log:
                log.log(now, member.id, str(member), True)

            # 既にいる人
            with Log(session.path) as log:
                for m in after.channel.members:
                    if m != member:
                        log.log(now, m.id, str(m), True)

            return

        # 退出
        if session.is_target(before.channel):
            now = datetime.datetime.now(timezone)

            session.enabled = False

            # 残っている人
            with Log(session.path) as log:
                for m in before.channel.members:
                    if m != member:
                        log.log(now, m.id, str(m), False)

            # 主
            with Log(session.path) as log:
                log.log(now, member.id, str(member), False)

            return

    # 参加勢
    elif session.enabled:
        now = datetime.datetime.now(timezone)

        # 参加
        if session.is_target(after.channel):
            with Log(session.path) as log:
                log.log(now, member.id, str(member), True)

            return

        # 退出
        if session.is_target(before.channel):
            with Log(session.path) as log:
                log.log(now, member.id, str(member), False)

            return


# 初期化
print('初期化しました')

# Botの起動とDiscordサーバーへの接続
bot.run(os.environ["DISCORD_TOKEN"])
