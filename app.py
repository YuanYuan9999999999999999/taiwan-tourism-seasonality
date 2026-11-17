from pathlib import Path
import pandas as pd
import streamlit as st
import altair as alt
import numpy as np

st.set_page_config(page_title='臺灣六縣市觀光季節分析', page_icon='🌤️', layout='wide')
CITIES=['臺北市','臺中市','臺南市','高雄市','花蓮縣','臺東縣']
COLORS=['#4C9AFF','#A78BFA','#FFB454','#F472B6','#34D399','#22D3EE']
YEAR_COLORS=['#60A5FA','#FBBF24','#A78BFA','#34D399']
def export_months(data):
    return data[['county','spot','year','month','visits','fixed','break_vs_prev_year']].sort_values(['county','spot','year','month']).rename(columns={'county':'縣市','spot':'景點','year':'年度','month':'月份','visits':'遊客人次','fixed':'四年完整樣本','break_vs_prev_year':'來源年度異常標記'})
@st.cache_data
def load():
    raw=pd.read_csv(Path(__file__).parent/'data/tourism.csv')
    raw=raw[raw.county.isin(CITIES)&raw.year.between(2022,2025)].copy()
    long=raw.melt(id_vars=['county','spot','year','break_vs_prev_year'],value_vars=[f'm{i}' for i in range(1,13)],var_name='month',value_name='visits')
    long['month']=long.month.str[1:].astype(int)
    long['visits']=pd.to_numeric(long.visits,errors='coerce')
    long.loc[long.visits<0,'visits']=float('nan')
    coverage=long.groupby(['county','spot']).agg(years=('year','nunique'),valid=('visits','count'),zeros=('visits',lambda x:(x==0).sum()))
    fixed=coverage[(coverage.years==4)&(coverage.valid==48)].index
    long['fixed']=pd.MultiIndex.from_frame(long[['county','spot']]).isin(fixed)
    return long,coverage

df,coverage=load()
st.title('臺灣六縣市觀光淡旺季')
st.caption('Seasonal Tourism in Taiwan: A Comparative Analysis of Six Cities · 2022–2025')
def reset_filters():
    st.session_state.update(cities=CITIES.copy(), years=[2022,2023,2024,2025], fixed=True, zero=False, distribution_scope='單一景點')
for key,value in dict(cities=CITIES.copy(),years=[2022,2023,2024,2025],fixed=True,zero=False).items():
    st.session_state.setdefault(key,value)
st.sidebar.header('探索條件')
st.sidebar.button('重設篩選',on_click=reset_filters)

cities=st.sidebar.multiselect('縣市',CITIES,key='cities',placeholder='選擇縣市')
years=st.sidebar.multiselect('年度',[2022,2023,2024,2025],key='years',placeholder='選擇年度')
fixed=st.sidebar.toggle('使用四年完整固定樣本',key='fixed')
zero=st.sidebar.toggle('排除四年內曾出現零值的景點',key='zero')
st.sidebar.caption('零值可能表示停業、未回報或真實零人次。預設保留原值；可切換觀察結果敏感度。')
x=df[df.county.isin(cities)&df.year.isin(years)].copy()
if fixed:x=x[x.fixed]
if zero:
    good=coverage[coverage.zeros==0].index
    x=x[pd.MultiIndex.from_frame(x[['county','spot']]).isin(good)]
if x.empty:st.info('請至少選擇一個有資料的縣市與年度。');st.stop()
a,b,c=st.columns(3)
a.metric('篩選景點數',len(x[['county','spot']].drop_duplicates()))
b.metric('篩選總人次',f'{x.visits.sum():,.0f}')
c.metric('缺漏月份',int(x.visits.isna().sum()))
st.caption('人次可重複計算，並非縣市不重複旅客數。固定樣本只能控制景點組成，無法排除統計方法或停業的影響。')
st.caption('目前範圍：'+'、'.join(cities)+'；年度：'+'、'.join(map(str,sorted(years))))
year_scale=alt.Scale(domain=[str(y) for y in sorted(years)],range=[YEAR_COLORS[y-2022] for y in sorted(years)])
tabs=st.tabs(['縣市總覽','淡旺季比較','景點探索','資料與方法'])
monthly=x.groupby(['county','year','month'],as_index=False).visits.sum(min_count=1)
monthly['date']=pd.to_datetime(dict(year=monthly.year,month=monthly.month,day=1))
with tabs[0]:
    st.subheader('每月遊客人次 · 折線圖')
    display_monthly=monthly.rename(columns={'date':'年月','visits':'遊客人次','county':'縣市'})
    color_scale=alt.Scale(domain=[c for c in CITIES if c in cities],range=[COLORS[CITIES.index(c)] for c in CITIES if c in cities])
    st.altair_chart(alt.Chart(display_monthly).mark_line(clip=True).encode(x=alt.X('年月:T',axis=alt.Axis(format='%Y/%m',tickCount=8,labelAngle=-30)),y=alt.Y('遊客人次:Q'),color=alt.Color('縣市:N',scale=color_scale),tooltip=['縣市:N',alt.Tooltip('年月:T',format='%Y-%m'),'遊客人次:Q']).add_params(alt.selection_interval(name='overview_zoom',bind='scales',clear='dblclick')),width='stretch')
    st.caption('圖內滾輪縮放、拖曳平移；雙擊圖內還原。右上角工具列可切換全螢幕。')
    st.subheader('各年度縣市比較 · 長條圖')
    annual=monthly.groupby(['county','year'],as_index=False).visits.sum(min_count=1).rename(columns={'county':'縣市','year':'年度','visits':'遊客人次'})
    annual['年度']=annual['年度'].astype(str)
    st.altair_chart(alt.Chart(annual).mark_bar().encode(x=alt.X('縣市:N',sort=CITIES,axis=alt.Axis(labelAngle=0)),y=alt.Y('遊客人次:Q',title='月資料加總人次'),color=alt.Color('年度:N',scale=year_scale,sort=[str(y) for y in sorted(years)]),xOffset='年度:N',tooltip=['縣市:N','年度:N',alt.Tooltip('遊客人次:Q',format=',.0f')]),width='stretch')
    st.subheader('每月人次組成 · 區域圖')
    st.altair_chart(alt.Chart(display_monthly).mark_area().encode(x=alt.X('年月:T',axis=alt.Axis(format='%Y/%m',tickCount=8,labelAngle=-30)),y=alt.Y('遊客人次:Q',stack='zero'),color=alt.Color('縣市:N',scale=color_scale),tooltip=['縣市:N',alt.Tooltip('年月:T',format='%Y-%m'),'遊客人次:Q']),width='stretch')
with tabs[1]:
    st.subheader('相對淡旺季 · 熱圖')
    monthly['index']=monthly.visits/monthly.groupby(['county','year']).visits.transform('mean').replace(0,float('nan'))
    heat=monthly.groupby(['county','month'],as_index=False)['index'].mean().rename(columns={'county':'縣市','month':'月份','index':'相對指數'})
    st.caption('每年先以「當月人次 ÷ 該年平均月人次」標準化，再平均所選年度。1 表示該年平均水準；大於 1 表示較旺。')
    st.altair_chart(alt.Chart(heat).mark_rect().encode(x=alt.X('月份:O',axis=alt.Axis(labelAngle=0)),y=alt.Y('縣市:N',sort=CITIES),color=alt.Color('相對指數:Q',scale=alt.Scale(scheme='blueorange',domainMid=1),title='相對指數'),tooltip=['縣市:N','月份:O',alt.Tooltip('相對指數:Q',format='.2f')]).properties(height=max(100,46*len(cities))),width='stretch')
    summer=monthly.groupby(['county','year']).apply(lambda g:g.loc[g.month.isin([7,8]),'visits'].sum()/g.visits.sum() if g.visits.sum()>0 else float('nan'),include_groups=False).rename('暑假人次占全年比例').reset_index()
    st.subheader('7、8 月人次占全年比例')
    summer=summer.rename(columns={'county':'縣市','year':'年度'})
    summer_table=summer.pivot(index='縣市',columns='年度',values='暑假人次占全年比例').reindex([c for c in CITIES if c in cities])
    summer_table.columns=summer_table.columns.astype(str)
    st.dataframe(summer_table.style.format('{:.1%}',na_rep='缺資料'))
with tabs[2]:
    st.caption('上方統計依側邊欄篩選；此頁可另選景點，並切換分布圖的分析對象。')
    city_col,spot_col=st.columns(2)
    city=city_col.selectbox('景點所在縣市',[c for c in CITIES if c in x.county.unique()])
    spots=sorted(x.loc[x.county==city,'spot'].unique())
    if spots:
        spot=spot_col.selectbox('觀光遊憩據點',spots)
        detail=x[(x.county==city)&(x.spot==spot)]
        detail_display=detail.rename(columns={'month':'月份','visits':'遊客人次','year':'年度'})
        detail_display['年度']=detail_display['年度'].astype(str)
        st.subheader(f'{city}・{spot}每月人次')
        st.altair_chart(alt.Chart(detail_display[['月份','遊客人次','年度']]).mark_line(point=True,clip=True).encode(x=alt.X('月份:Q',scale=alt.Scale(domain=[1,12],nice=False,zero=False),axis=alt.Axis(values=list(range(1,13)),format='d')),y=alt.Y('遊客人次:Q'),color=alt.Color('年度:N',scale=year_scale,sort=[str(y) for y in sorted(years)]),tooltip=['年度:N','月份:O',alt.Tooltip('遊客人次:Q',format=',.0f')]).add_params(alt.selection_interval(name='spot_zoom',bind='scales',clear='dblclick')),width='stretch')
        st.caption('圖內滾輪縮放、拖曳平移；雙擊圖內還原。右上角工具列可切換全螢幕。')
        if detail.break_vs_prev_year.any():st.info('此景點有來源標記的年度異常變動，原因需要另查，不能直接判定為統計方式改變。')
    st.divider()
    st.subheader('人次分布比較')
    scope=st.radio('分布圖分析對象',['單一景點','單一縣市','跨縣市比較'],horizontal=True,key='distribution_scope')
    distribution=detail if scope=='單一景點' else x[x.county==city] if scope=='單一縣市' else x
    scope_name=city+'・'+spot if scope=='單一景點' else city if scope=='單一縣市' else f'已選 {distribution.county.nunique()} 縣市'
    period='、'.join(map(str,sorted(years)))+' 年'
    st.caption(f'分析對象：{scope_name}｜{period}｜有效 {distribution.visits.count():,} 筆、缺漏 {distribution.visits.isna().sum():,} 筆景點月資料。')
    if scope=='跨縣市比較':st.caption('比較範圍：'+'、'.join(c for c in CITIES if c in distribution.county.unique()))
    st.download_button('下載此分析對象的月資料',export_months(distribution).to_csv(index=False).encode('utf-8-sig'),'tourism-distribution.csv','text/csv')
    st.subheader(f'{scope_name}｜月人次分布・直方圖')
    hist_mode=st.radio('直方圖分組',['對數間距分組','等寬分組'],horizontal=True)
    values=distribution.visits.dropna()
    if len(values):
        maximum=float(values.max())
        minimum=float(values.min())
        positive_log=hist_mode=='對數間距分組' and minimum>0 and maximum>minimum
        edges=np.expm1(np.linspace(0,np.log1p(max(maximum,1)),26)) if hist_mode=='對數間距分組' else np.linspace(0,max(maximum,1),26)
        if positive_log:edges=np.geomspace(minimum,maximum,26)
        edges[0]=minimum if positive_log else 0
        edges[-1]=max(maximum,1)
        counts,edges=np.histogram(values,bins=edges)
        hist=pd.DataFrame({'下界':edges[:-1],'上界':edges[1:],'筆數':counts})
        hs=alt.Scale(type='symlog',constant=1,zero=True,nice=False,domain=[0,max(maximum,1)]) if hist_mode=='對數間距分組' else alt.Scale(zero=True,nice=False,domain=[0,max(maximum,1)])
        if positive_log:hs=alt.Scale(type='log',nice=False,domain=[minimum,maximum])
        hist_ticks=np.geomspace(minimum,maximum,6).tolist() if positive_log else [v for v in [0,10,100,1000,10000,100000,1000000,10000000] if v<=max(maximum,1)]
        st.altair_chart(alt.Chart(hist).mark_bar(orient='vertical').encode(x=alt.X('下界:Q',title='景點單月人次',scale=hs,axis=alt.Axis(format=',.0f',values=hist_ticks if hist_mode=='對數間距分組' else alt.Undefined,grid=False)),x2='上界:Q',y=alt.Y('筆數:Q',title='景點月份筆數',axis=alt.Axis(tickMinStep=1)),y2=alt.Y2(datum=0),tooltip=[alt.Tooltip('下界:Q',format=',.1f'),alt.Tooltip('上界:Q',format=',.1f'),'筆數:Q']),width='stretch')
        st.caption(('對數間距分組依目前資料範圍設定，低人次區間較細、高人次區間較寬。' if hist_mode=='對數間距分組' else '等寬分組在原始人次尺度上劃分相同寬度的區間。')+'柱高表示各區間筆數，包含目前範圍的全部有效值與零值；缺漏值不納入。')
    st.subheader(f'{scope_name}｜月人次分布・箱型圖')
    box_scale = st.radio('人次刻度', ['對稱對數刻度', '原始刻度'], horizontal=True)
    scale = alt.Scale(type='symlog', constant=10000, zero=True) if box_scale == '對稱對數刻度' else alt.Scale(zero=True)
    box_data=distribution[['county','visits']].rename(columns={'county':'縣市','visits':'景點單月人次'})
    box = alt.Chart(box_data).mark_boxplot(
        extent=1.5, size=28,
        median={'color': 'white', 'strokeWidth': 2},
        rule={'color':'#9CA3AF'}, ticks={'color':'#9CA3AF'},
        outliers={'size': 12, 'opacity': 0.3},
    ).encode(
        y=alt.Y('縣市:N', title=None, sort=CITIES, axis=alt.Axis(labelAngle=0)),
        x=alt.X('景點單月人次:Q', title='景點單月人次', scale=scale, axis=alt.Axis(format=',.0f',tickCount=6,grid=False, values=[0,1000,10000,100000,1000000,10000000] if box_scale=='對稱對數刻度' else alt.Undefined)),
        color=alt.Color('縣市:N', sort=CITIES, scale=alt.Scale(domain=CITIES,range=COLORS), legend=None),
    ).properties(height=max(140,60*distribution.county.nunique()))
    st.altair_chart(box, width='stretch')
    if box_scale == '對稱對數刻度':
        st.caption('對稱對數刻度保留零值並壓縮較大數值；刻度間距不代表相同的人次差。四分位數與離群值仍以原始人次計算。')
    st.caption('每筆觀測為一個景點的一個月份。箱體涵蓋中間 50% 的數值，白線為中位數；鬚延伸至 1.5 倍四分位距內的最遠觀測值，圓點為其外的觀測值。全部資料均保留。')
with tabs[3]:
    st.markdown('''### 資料來源與範圍
原始來源：[交通部觀光署](https://data.gov.tw/dataset/8116)。本網站內附 [觀光放大鏡整理 CSV](https://tourismlens.dream-coders.com/data/tourismlens-spots.csv)，使用六縣市 2022～2025 年資料。

整理者說明 2024 年起使用觀光署統計資料庫單月表，詳見[整理者的來源與方法說明](https://tourismlens.dream-coders.com/method/)。2025 年來源依整理者揭露，尚未逐筆對照官方匯出。授權：政府資料開放授權條款第 1 版。

### 處理規則
- 月欄位轉長格式，非數值及負值視為缺漏，零值保留並提供敏感度篩選。
- 固定樣本重新以 2022～2025 年皆有資料、共 48 個有效月份判定，未直接採用來源的全歷史固定樣本標記。
- 年人次採月資料加總，與來源的年度合計可能不同。
- 景點沿用整理者名稱；尚未逐一驗證更名與統計範圍。異常變動標記僅供查核。
- 選擇全部樣本時，各年度景點數可能不同。疫情、災害、休園及統計變動都可能影響季節比較。

''')
    st.subheader('納入景點的四年資料完整度')
    st.caption('僅列目前篩選納入的景點；年數、有效月份及零值月份均以 2022～2025 四年計算。')
    selected_keys=pd.MultiIndex.from_frame(x[['county','spot']].drop_duplicates())
    st.dataframe(coverage.loc[coverage.index.isin(selected_keys)].reset_index().rename(columns={'county':'縣市','spot':'景點','years':'資料年數','valid':'有效月份','zeros':'零值月份'}),hide_index=True)
    st.subheader('下載篩選資料')
    export=export_months(x)
    st.caption(f'下載側邊欄篩選後的 {len(export):,} 筆月資料，包含所選縣市的全部納入景點。景點探索頁的單一景點選擇不影響此下載。')
    st.download_button('下載目前篩選的月資料',export.to_csv(index=False).encode('utf-8-sig'),'tourism-filtered.csv','text/csv')
