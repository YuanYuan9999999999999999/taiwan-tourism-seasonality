from pathlib import Path
import pandas as pd
import streamlit as st
import altair as alt
import numpy as np

st.set_page_config(page_title='臺灣六縣市觀光季節分析', page_icon='🌤️', layout='wide')
CITIES=['臺北市','臺中市','臺南市','高雄市','花蓮縣','臺東縣']
COLORS=['#4C9AFF','#A78BFA','#FFB454','#F472B6','#34D399','#22D3EE']
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
st.sidebar.header('探索條件')
cities=st.sidebar.multiselect('縣市',CITIES,default=CITIES)
years=st.sidebar.multiselect('年度',[2022,2023,2024,2025],default=[2022,2023,2024,2025])
fixed=st.sidebar.toggle('使用四年完整固定樣本',value=True)
zero=st.sidebar.toggle('排除四年內曾出現零值的景點',value=False)
st.sidebar.caption('零值可能表示停業、未回報或真實零人次。預設保留原值；可切換觀察結果敏感度。')
x=df[df.county.isin(cities)&df.year.isin(years)].copy()
if fixed:x=x[x.fixed]
if zero:
    good=coverage[coverage.zeros==0].index
    x=x[pd.MultiIndex.from_frame(x[['county','spot']]).isin(good)]
if x.empty:st.info('請至少選擇一個有資料的縣市與年度。');st.stop()
a,b,c=st.columns(3)
a.metric('納入景點',len(x[['county','spot']].drop_duplicates()))
b.metric('納入景點人次',f'{x.visits.sum():,.0f}')
c.metric('缺漏月份',int(x.visits.isna().sum()))
st.caption('人次可重複計算，並非縣市不重複旅客數。固定樣本只能控制景點組成，無法排除統計方法或停業的影響。')
tabs=st.tabs(['縣市總覽','淡旺季比較','景點探索','資料與方法'])
monthly=x.groupby(['county','year','month'],as_index=False).visits.sum(min_count=1)
monthly['date']=pd.to_datetime(dict(year=monthly.year,month=monthly.month,day=1))
with tabs[0]:
    st.subheader('每月遊客人次 · 折線圖')
    display_monthly=monthly.rename(columns={'date':'年月','visits':'遊客人次','county':'縣市'})
    color_scale=alt.Scale(domain=CITIES,range=COLORS)
    st.altair_chart(alt.Chart(display_monthly).mark_line().encode(x=alt.X('年月:T'),y=alt.Y('遊客人次:Q'),color=alt.Color('縣市:N',scale=color_scale),tooltip=['縣市:N',alt.Tooltip('年月:T',format='%Y-%m'),'遊客人次:Q']),width='stretch')
    st.subheader('各年度縣市比較 · 長條圖')
    annual=monthly.groupby(['county','year'],as_index=False).visits.sum(min_count=1)
    st.altair_chart(alt.Chart(annual).mark_bar().encode(x=alt.X('county:N',title='縣市'),y=alt.Y('visits:Q',title='月資料加總人次'),color=alt.Color('year:N',title='年度'),xOffset='year:N',tooltip=[alt.Tooltip('county:N',title='縣市'),alt.Tooltip('year:O',title='年度'),alt.Tooltip('visits:Q',title='人次',format=',.0f')]),width='stretch')
    st.subheader('每月人次組成 · 區域圖')
    st.altair_chart(alt.Chart(display_monthly).mark_area().encode(x=alt.X('年月:T'),y=alt.Y('遊客人次:Q',stack='zero'),color=alt.Color('縣市:N',scale=color_scale),tooltip=['縣市:N',alt.Tooltip('年月:T',format='%Y-%m'),'遊客人次:Q']),width='stretch')
with tabs[1]:
    st.subheader('相對淡旺季 · 熱圖')
    monthly['index']=monthly.visits/monthly.groupby(['county','year']).visits.transform('mean').replace(0,float('nan'))
    heat=monthly.groupby(['county','month'],as_index=False)['index'].mean()
    st.caption('每年先以「當月人次 ÷ 該年平均月人次」標準化，再平均所選年度。1 表示該年平均水準；大於 1 表示較旺。')
    st.altair_chart(alt.Chart(heat).mark_rect().encode(x=alt.X('month:O',title='月份'),y=alt.Y('county:N',title='縣市'),color=alt.Color('index:Q',scale=alt.Scale(scheme='blueorange',domainMid=1),title='相對指數'),tooltip=[alt.Tooltip('county:N',title='縣市'),alt.Tooltip('month:O',title='月份'),alt.Tooltip('index:Q',title='相對指數',format='.2f')]).properties(height=280),width='stretch')
    summer=monthly.groupby(['county','year']).apply(lambda g:g.loc[g.month.isin([7,8]),'visits'].sum()/g.visits.sum() if g.visits.sum()>0 else float('nan'),include_groups=False).rename('暑假人次占全年比例').reset_index()
    st.subheader('7、8 月人次占全年比例')
    summer=summer.rename(columns={'county':'縣市','year':'年度'})
    st.dataframe(summer.style.format({'暑假人次占全年比例':'{:.1%}'}),hide_index=True)
    st.caption('均勻分布時兩個月約占 16.7%。比例高低是描述性比較，無法單獨證明暑假造成旅遊增加。')
with tabs[2]:
    city=st.selectbox('景點所在縣市',cities)
    spots=sorted(x.loc[x.county==city,'spot'].unique())
    if spots:
        spot=st.selectbox('觀光遊憩據點',spots)
        detail=x[(x.county==city)&(x.spot==spot)]
        detail_display=detail.rename(columns={'month':'月份','visits':'遊客人次','year':'年度'})
        detail_display['年度']=detail_display['年度'].astype(str)
        st.line_chart(detail_display,x='月份',y='遊客人次',color='年度')
        if detail.break_vs_prev_year.any():st.info('此景點有來源標記的年度異常變動，原因需要另查，不能直接判定為統計方式改變。')
    scope=st.radio('分布圖範圍',['所有已選縣市','目前縣市','目前景點'],horizontal=True)
    distribution=x if scope=='所有已選縣市' else x[x.county==city]
    if scope=='目前景點' and spots:distribution=detail
    st.caption(f'以下直方圖與箱型圖範圍：{scope}；共 {len(distribution):,} 筆景點月份資料。')
    st.subheader('景點月人次分布 · 直方圖')
    hist_mode=st.radio('直方圖分組',['對數間距分組','等寬分組'],horizontal=True)
    values=distribution.visits.dropna()
    if len(values):
        maximum=float(values.max())
        edges=np.expm1(np.linspace(0,np.log1p(max(maximum,1)),26)) if hist_mode=='對數間距分組' else np.linspace(0,max(maximum,1),26)
        edges[-1]=max(maximum,1)
        counts,edges=np.histogram(values,bins=edges)
        hist=pd.DataFrame({'下界':edges[:-1],'上界':edges[1:],'筆數':counts})
        hs=alt.Scale(type='symlog',constant=1,zero=True) if hist_mode=='對數間距分組' else alt.Scale(zero=True)
        st.altair_chart(alt.Chart(hist).mark_bar(orient='vertical').encode(x=alt.X('下界:Q',title='景點單月人次',scale=hs,axis=alt.Axis(format=',.0f',values=[0,10,100,1000,10000,100000,1000000,10000000] if hist_mode=='對數間距分組' else alt.Undefined,grid=False)),x2='上界:Q',y=alt.Y('筆數:Q',title='景點月份筆數'),y2=alt.Y2(datum=0),tooltip=[alt.Tooltip('下界:Q',format=',.1f'),alt.Tooltip('上界:Q',format=',.1f'),'筆數:Q']),width='stretch')
        st.caption('對數間距分組讓低人次區間更細、高人次區間更寬；柱高表示各區間筆數，全部有效值與零值均納入。切換等寬分組可查看原始人次尺度。')
    st.subheader('景點月人次分布 · 箱型圖')
    box_scale = st.radio('人次刻度', ['對稱對數刻度', '原始刻度'], horizontal=True)
    scale = alt.Scale(type='symlog', constant=10000, zero=True) if box_scale == '對稱對數刻度' else alt.Scale(zero=True)
    box = alt.Chart(distribution).mark_boxplot(
        extent=1.5, size=28,
        median={'color': 'white', 'strokeWidth': 2},
        rule={'color':'#9CA3AF'}, ticks={'color':'#9CA3AF'},
        outliers={'size': 12, 'opacity': 0.3},
    ).encode(
        y=alt.Y('county:N', title=None, sort=CITIES, axis=alt.Axis(labelAngle=0)),
        x=alt.X('visits:Q', title='景點單月人次', scale=scale, axis=alt.Axis(format=',.0f', values=[0,1000,10000,100000,1000000,10000000] if box_scale=='對稱對數刻度' else alt.Undefined)),
        color=alt.Color('county:N', sort=CITIES, scale=alt.Scale(domain=CITIES,range=COLORS), legend=None),
    ).properties(height=360)
    st.altair_chart(box, width='stretch')
    if box_scale == '對稱對數刻度':
        st.caption('對稱對數刻度保留零值並壓縮較大數值；刻度間距不代表相同的人次差。四分位數與離群值仍以原始人次計算。')
    st.caption('每筆觀測為一個景點的一個月份。箱體涵蓋中間 50% 的數值，白線為中位數；鬚延伸至 1.5 倍四分位距內的最遠觀測值，圓點為其外的觀測值。全部資料均保留。')
with tabs[3]:
    st.markdown('''### 資料來源與範圍
原始來源：[交通部觀光署](https://data.gov.tw/dataset/8116)。本網站內附 [觀光放大鏡整理 CSV](https://tourismlens.dream-coders.com/data/tourismlens-spots.csv)，使用六縣市 2022～2025 年資料。

整理者說明 2024 年起使用觀光署統計資料庫單月表，詳見[資料與方法](https://tourismlens.dream-coders.com/method/)。2025 年來源依整理者揭露，尚未逐筆對照官方匯出。授權：政府資料開放授權條款第 1 版。

### 處理規則
- 月欄位轉長格式，非數值及負值視為缺漏，零值保留並提供敏感度篩選。
- 固定樣本重新以 2022～2025 年皆有資料、共 48 個有效月份判定，未直接採用來源的全歷史固定樣本標記。
- 年人次採月資料加總，與來源的年度合計可能不同。
- 景點沿用整理者名稱；尚未逐一驗證更名與統計範圍。異常變動標記僅供查核。
- 選擇全部樣本時，各年度景點數可能不同。疫情、災害、休園及統計變動都可能影響季節比較。

### 分析問題
六縣市旺季是否相同？花蓮、臺東的暑假占比是否較高？哪些景點的月人次起伏明顯？請根據圖表提出觀察，另查證原因。
''')
    st.dataframe(coverage.reset_index().rename(columns={'county':'縣市','spot':'景點','years':'資料年數','valid':'有效月份','zeros':'零值月份'}),hide_index=True)
    st.download_button('下載目前篩選的月資料',x.to_csv(index=False).encode('utf-8-sig'),'tourism-filtered.csv','text/csv')
