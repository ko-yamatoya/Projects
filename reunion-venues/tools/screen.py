# 食べログ詳細から「15名・日曜・うるさくない・高くない」の一次ふるい → screen.json
#   python3 screen.py        # 結果の件数と落ちた理由の内訳を表示
import json, re, collections

# 同窓会の1軒目に向かないジャンル（食事が主役でない／大人数で囲めない／単価が跳ねる）
EXCL_GENRE = ['バー','カフェ','喫茶店','ラーメン','つけ麺','立ち飲み','パン','スイーツ','ケーキ','カレー',
              '定食・食堂','寿司','天ぷら','とんかつ','うどん','そば','牛丼','ハンバーガー','ショーレストラン',
              'クラブ','ラウンジ','ビュッフェ','バイキング','パフェ','甘味処','ダーツ']
# 業態として「大衆」「立ち飲み」は賑やかさが売りなので落とす
LOUD_NAME = ['立ち飲み','立飲み','大衆酒場','大衆居酒屋','せんべろ','センベロ']
# 口コミ中の騒がしさの言及
NOISY = ['うるさ','騒がし','騒々し','声が聞こえ','声が大き','会話が聞こえ','音楽が大き','BGMが大き','爆音','話し声が響','ガヤガヤ']
CALM  = ['落ち着','静か','ゆっくり話','会話を楽し','話しやす','ゆっくりでき']

def rng(s):
    """「10～20人可」「20人～50人可」「20人以下可」「30人以上可」「8人可」を (下限, 上限) に"""
    out=[]; used=[]
    for m in re.finditer(r'(\d+)\s*人?\s*[～~]\s*(\d+)\s*人可', s):
        out.append((int(m.group(1)), int(m.group(2)))); used.append(m.span())
    for m in re.finditer(r'(\d+)\s*人以下可', s): out.append((1, int(m.group(1)))); used.append(m.span())
    for m in re.finditer(r'(\d+)\s*人以上可', s): out.append((int(m.group(1)), 999)); used.append(m.span())
    for m in re.finditer(r'(\d+)\s*人可', s):
        if not any(a<=m.start()<b for a,b in used): out.append((int(m.group(1)), int(m.group(1))))
    return out

def span_label(a, b):
    return f"{a}名〜" if b>=999 else f"{a}〜{b}名"

def room_for(n, t):
    """15名で入れる個室があるか。区分の表記＋備考の「最大N名」の両方を見る"""
    s=t.get('個室') or ''
    if not s.startswith('有'): return None
    head=re.search(r'（(.*?)）', s)
    rs=rng(head.group(1)) if head else []
    fits=[r for r in rs if r[0]<=n<=r[1]]
    if fits: return dict(kind='個室', label='個室 '+span_label(*fits[0]), exact=True)
    note=s[(head.end() if head else 0):]
    m=[int(x) for x in re.findall(r'(?:最大|～|~)\s*(\d{2,3})\s*名', note)]
    if m and max(m)>=n: return dict(kind='個室', label=f"個室 最大{max(m)}名（店の備考より）", exact=False)
    big=[r for r in rs if r[0]>n]
    if big: return dict(kind='個室(大)', label=f"個室 {span_label(*big[0])}（{n}名で使えるか要確認）", exact=False)
    return None

def charter_for(n, t):
    s=t.get('貸切') or ''
    if not s.startswith('可'): return None
    rs=rng(s)
    if any(r[1]<=20 for r in rs): return dict(kind='貸切', label='貸切 20名以下可', small=True)
    if rs: return dict(kind='貸切', label='貸切 '+'、'.join(span_label(a,b) for a,b in sorted(rs)), small=False)
    return dict(kind='貸切', label='貸切可（人数は店に確認）', small=False)

DAYTOK=r'((?:(?:月|火|水|木|金|土|日|祝日|祝前日|祝後日)・?)+)'
def has_sun(days): return bool(re.search(r'(^|・)日(・|$)', days))
def sunday(t):
    """日曜の夜（21時以降まで）営業しているか: True / False / None(判定不能)"""
    h=(t.get('営業時間') or '')
    first=h.split('■')[0]; rest='■'.join(h.split('■')[1:])
    for m in re.finditer(DAYTOK+r'\s*定休日', first):
        if has_sun(m.group(1)): return False
    if re.search(r'定休日[^■]{0,20}日曜|日曜[^■]{0,6}(定休|休み)', rest) and '日曜営業' not in rest: return False
    # 曜日の並びごとに区切り、その区間にある時間帯を全部見る（昼の部の後ろに夜の部が続く）
    toks=[m for m in re.finditer(DAYTOK+r'(?=\s*\d{1,2}:\d{2})', first)]
    if not toks:
        ends=[int(b) for b in re.findall(r'\d{1,2}:\d{2}\s*-\s*(\d{1,2}):\d{2}', first)]
        return (any(e>=21 or e<=5 for e in ends)) if ends else None
    sun_seen=False; unreadable=False
    for i,m in enumerate(toks):
        seg=first[m.end(): toks[i+1].start() if i+1<len(toks) else len(first)]
        if not has_sun(m.group(1)): continue
        sun_seen=True
        ends=[int(b) for b in re.findall(r'\d{1,2}:\d{2}\s*-\s*(\d{1,2}):\d{2}', seg)]
        if any(e>=21 or e<=5 for e in ends): return True
        if not ends: unreadable=True     # 「翌02:00」など読めない書き方は落とさず判定不能にする
    if unreadable or not sun_seen: return None
    return False

def charge(t):
    s=t.get('サービス料・ チャージ') or ''
    m=re.search(r'サービス料[^0-9０-９]{0,6}([0-9０-９]{1,2})\s*[%％]', s)
    return (int(m.group(1)) if m else 0), s[:120]

if __name__=='__main__':
    N=15
    tb=json.load(open('tabelog_detail.json'))
    out=[]; why=collections.Counter()
    for d in tb:
        t=d['tbl']; g=t.get('ジャンル') or d['genres']
        gl=[x.strip() for x in re.split(r'[、,]', g)]
        if gl and gl[0] in EXCL_GENRE: why['ジャンル']+=1; continue
        if any(w in d['name']+g for w in LOUD_NAME): why['大衆・立ち飲み']+=1; continue
        sp=t.get('空間・設備') or ''
        # 「スポーツ観戦可」は多くがテレビがあるだけの区分で、落とすと静かな中華や韓国料理まで消える（83軒中75軒がこれ）。
        # 騒がしさの目安になる「ライブ・生演奏あり」だけで落とす
        if 'ライブ・生演奏あり' in sp: why['ライブ・生演奏']+=1; continue
        sun=sunday(t)
        if sun is False: why['日曜の夜に営業していない']+=1; continue
        room=room_for(N,t); ch=charter_for(N,t)
        mx=re.search(r'着席時\s*(\d+)\s*人', t.get('最大予約可能人数') or '')
        maxseat=int(mx.group(1)) if mx else None
        if maxseat is not None and maxseat<N: why['最大予約人数<15']+=1; continue
        if not room and not (ch and ch['small']):
            why['15名の個室も小さな貸切も無い']+=1; continue
        sc,chg=charge(t)
        text=' '.join(d.get('sample_reviews') or [])
        noisy=sum(text.count(w) for w in NOISY); calm=sum(text.count(w) for w in CALM)
        out.append(dict(id=d['id'], name=d['name'], area=d['area'], score=d['score'], reviews=d['reviews'],
                        budget=d['budget_dinner'], genre=g, room=room, charter=ch, maxseat=maxseat,
                        sunday=sun, service_pct=sc, charge_text=chg, calm_space='落ち着いた空間' in sp,
                        noisy_hits=noisy, calm_hits=calm, lat=d.get('lat'), lon=d.get('lon'), url=d['url']))
    json.dump(out, open('screen.json','w'), ensure_ascii=False, indent=1)
    print('in',len(tb),'pass',len(out)); print(why.most_common())
    c=collections.Counter((x['area'], x['room']['kind'] if x['room'] else '貸切のみ') for x in out); print(c)
    print('日曜判定不能', sum(1 for x in out if x['sunday'] is None), ' サービス料あり', sum(1 for x in out if x['service_pct']))
