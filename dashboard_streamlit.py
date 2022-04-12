#streamlit run teste_streamlit.py # linkar a pagina streamlit com o arquivo
import folium
import geopandas
import numpy  as np
import pandas as pd
import pydeck as pdk
import seaborn as sns
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
import plotly.figure_factory as ff
import plotly.graph_objects as go

from numerize.numerize import numerize
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
from datetime import datetime, date
from PIL import Image
from io import BytesIO

# =======================
# INITIAL CONFIGURATIONS
# =======================

st.set_page_config(page_title='Company Dashboard', layout='wide', page_icon="📊" ) #centered ou wide

title_format = '<div> <p style="font-family:sans-serif;' \
                'color:#33FF68 ;' \
                'font-size: 50px;' \
                'font-weight: bold;' \
                'font-style: italic;' \
                'text-align: left;">' \
                'Real State Company</p> </div'
st.markdown(title_format, unsafe_allow_html=True)

subtitle_format = '<p style="font-family:sans-serif;' \
                     'color:#81E795;' \
                     'font-size: 25px;' \
                     'font-style: italic;' \
                     'text-align: left;' \
                     '">Strategic Dashboard</p>'
st.markdown(subtitle_format, unsafe_allow_html=True)
st.markdown('---')

st.sidebar.title('Interactive Menu')
image = Image.open('banner.png')
st.sidebar.image(image,use_column_width=True,caption='Find what you are looking for!')
st.sidebar.title('Filter Options')


# =======================
# FUNCTIONS DEFINITIONS
# =======================

@st.cache(allow_output_mutation=True)
def get_data(path):
    data = pd.read_csv(path, parse_dates=['date'])
    return data

@st.cache(allow_output_mutation=True)
def get_geofile(url):
    geofile = geopandas.read_file(url)
    return geofile

def filters(data):
    filter_yr_built = st.sidebar.slider('Year Built', int(data['yr_built'].min()), int(data['yr_built'].max()),
                                       (int(data['yr_built'].min()+15), int(data['yr_built'].max()-15)))

    min_date = datetime.strptime(str(data['date'].min()), '%Y-%m-%d %H:%M:%S').date()
    max_date = datetime.strptime(str(data['date'].max()), '%Y-%m-%d %H:%M:%S').date()
    filter_date = st.sidebar.slider('Date', min_date, max_date, (min_date,max_date))     

    min_price = int(data['price'].min())
    max_price = int(data['price'].max())
    offset = 500000
    filter_price = st.sidebar.slider('Price', min_price, max_price, (min_price+offset, max_price-offset))

    filter_waterfront = st.sidebar.checkbox('Only waterfront houses')
    filter_renovated = st.sidebar.checkbox('Only renovated houses')
    
    
    filtered_data = data[(data['price'] > filter_price[0]) & (data['price'] < filter_price[1]) & 
                         (data['yr_built'] > filter_yr_built[0]) & (data['yr_built'] < filter_yr_built[1]) &
                         (data['date'] > pd.to_datetime(filter_date[0])) & (data['date'] < pd.to_datetime(filter_date[1])) &
                         (data['waterfront'] == filter_waterfront) & (data['renovated'] == filter_renovated)]
    st.sidebar.markdown('---')
    st.sidebar.markdown('Total Filtered Houses: {}'.format(filtered_data.shape[0]))
    
    return filtered_data


def feature_engineering(aux2):
    # Creating feature 'renovated'
    aux2['renovated'] = aux2['yr_renovated'].apply(lambda x: 1 if x > 0 else 0)
                
    # Creating feature year_month
    aux2['year_month'] = aux2['date'].dt.strftime('%Y-%m')
                
    # Creating feature year_week
    aux2['year_week'] = aux2['date'].dt.strftime('%Y-%U')
                

    return aux2

def kpis(data):
    st.title('Business Overview')
    today = date.today()
    today = today.strftime("%B %d, %Y")
    st.markdown(today)
    
    invested = data['price'].sum()
    income = data['sell_price'].sum()
    profit = data['partial_profit'].sum()
    income_perc = str(round((income*100/invested),2)) + '%'
    profit_perc = str(round((profit*100/invested),2)) + '%'
    
    col1, col2, col3= st.columns([3,1,3])
    with col2:
        st.markdown(' ')
        st.markdown(' ')
        st.markdown('')
        st.metric("Total Invested", numerize(invested))
        st.metric("Recommended Houses", data.shape[0])
        st.metric("Expected Income", numerize(income), income_perc)
        st.metric("Expected Profit", numerize(profit), profit_perc)
    
    with col1:
        # Create distplot with custom bin_size
        average_year_month = data[['year_month','price']].groupby('year_month').mean().reset_index()
        fig = px.line(average_year_month, x="year_month", y="price", title='Average Value of Recommended Houses', width=500)
        fig.update_layout(yaxis_title="Average Price (US$)", xaxis_title=" ")
    
        # Plot!
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        df = data[['id', 'lat', 'long']].copy()
        st.markdown('Density of Recommended Houses')
        st.pydeck_chart(pdk.Deck(
             map_style='mapbox://styles/mapbox/light-v9',
             initial_view_state=pdk.ViewState(
                 latitude=47.60,
                 longitude=-122.33,
                 zoom=10,
                 pitch=50,
             ),
             layers=[
                 pdk.Layer(
                    'HexagonLayer',
                    data=df,
                    get_position='[long, lat]',
                    radius=200,
                    elevation_scale=4,
                    elevation_range=[0, 1000],
                    pickable=True,
                    extruded=True,
                 ),
                 pdk.Layer(
                     'ScatterplotLayer',
                     data=df,
                     get_position='[long, lat]',
                     get_color='[200, 30, 0, 160]',
                     get_radius=200,
                 ),
             ],
         ))
    df_download(data)
    st.markdown('---')
    return None

def df_download(data):
    with st.expander("Click here if you want to download the list of the recommended houses!"):
        choosen_cols = st.multiselect(label='Select the columns you want:', options=data.columns)
        if (choosen_cols == []):
            datadown = data
        else:
            datadown = data[choosen_cols]
        st.dataframe(data=datadown, width=600)
        
        st.write('**Attention: The filters on the sidebar will not effect this chart!!!**')
        st.write('If you are sure about the choosed columns, press the button below:')
        datadown_csv = datadown.to_csv()
        st.download_button(label='Download file as .csv',data=datadown_csv, file_name='recommendations.csv')

def portfolio_density(data, geofile):
    st.title('Geographic Information')
    with st.spinner('Loading map...'):
        c1, c2 = st.columns((1, 1))
        c1.header('House Distribution')
 
        # Base Map - Folium
        density_map = folium.Map(location=[data['lat'].mean(), data['long'].mean()],
                                 default_zoom_start=15)
        market_cluster = MarkerCluster().add_to(density_map)
        for name, row in data.iterrows():
            folium.Marker([row['lat'], row['long']],
                          popup='Sold R${0} on: {1}. Features: {2} sqft, {3} bedrooms, {4} bathrooms, year built: {5}'.format(
                              row['price'],
                              row['date'],
                              row['sqft_living'],
                              row['bedrooms'],
                              row['bathrooms'],
                              row['yr_built'])).add_to(market_cluster)

        with c1:
            folium_static(density_map)

        # Region Price Map
        c2.header('Price Density')

        df = data[['price', 'zipcode']].groupby('zipcode').mean().reset_index()
        df.columns = ['ZIP', 'PRICE']

        # df = df.sample(10)

        geofile = geofile[geofile['ZIP'].isin(df['ZIP'].tolist())]
        region_price_map = folium.Map(location=[data['lat'].mean(), data['long'].mean()],
                                      default_zoom_start=15)
        region_price_map.choropleth(data=df,
                                    geo_data=geofile,
                                    columns=['ZIP', 'PRICE'],
                                    key_on='feature.properties.ZIP',
                                    fill_color='YlOrRd',  # yellow orange red
                                    fill_opacity=0.7,
                                    line_opacity=0.2,
                                    legend_name='AVG PRICE')

        with c2:
            folium_static(region_price_map)

    return None

def std_font(ax1, title, xlabel, ylabel):
    ax1.set_title(title, loc='left', fontdict={'fontsize': 18}, pad=20)
    ax1.set_xlabel(xlabel, fontdict={'fontsize': 12, 'style': 'italic'})
    ax1.set_ylabel(ylabel, fontdict={'fontsize': 12, 'style': 'italic'})
    return None

def plots(aux2):
    st.title('Locality Analysis')
    
    aux3 = aux2.query('city != " N/A"')
    # House density plots
    # Create distplot with custom bin_size
    price_city = aux3[['city','price']].groupby('city').mean().reset_index().sort_values(by='price', ascending=False).head(10)
    fig = px.bar(price_city, x="city", y="price", title='Average Price by City')
    fig.update_layout(yaxis_title="Average Price (US$)", xaxis_title="City")    
    # Plot!
    st.plotly_chart(fig, use_container_width=True)
    
    aux3 = aux2.query('road != " N/A"')
    # House density plots
    # Create distplot with custom bin_size
    price_road = aux3[['road','price']].groupby('road').mean().reset_index().sort_values(by='price', ascending=False).head(10)
    fig = px.bar(price_road, x="road", y="price", title='Average Price by Road')
    fig.update_layout(yaxis_title="Average Price (US$)", xaxis_title="Road")    
    # Plot!
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('---')
    
    st.title('Time-based Analysis')
    
    # Year_month plot
    count_year_month = aux2[['year_month','price']].groupby('year_month').count().reset_index()
    average_year_month = aux2[['year_month','price']].groupby('year_month').mean().reset_index()

    fig = plt.figure(figsize=(11,5), tight_layout={'pad':2.0})
    ax1 = plt.subplot(2,1,1)
    ax = sns.barplot(data=count_year_month, x='year_month', y='price')
    std_font(ax, 'Amount of Sold Houses', '', 'Count')

    ax2 = plt.subplot(2,1,2)
    sns.lineplot(data=average_year_month, x='year_month', y='price')
    std_font(ax2, 'Average Value of Sold Houses', '', 'Average Price (US$)')
    buf = BytesIO()
    fig.savefig(buf, format="png")
    st.image(buf)
    

    # Year_week plot
    sales_week = aux2[['price', 'year_week']].groupby('year_week').sum().reset_index()
    average_sales = aux2[['price', 'year_week']].groupby('year_week').sum()['price'].mean()

    fig = plt.figure( figsize=(11, 6) )
    plt.axhline( average_sales, linestyle='--', label='Average')
    ax1 = sns.lineplot(data=sales_week.sort_values('year_week'), x='year_week', y='price', ci=None)
    std_font(ax1, 'Sum of House sales over the weeks', '', 'Price (US$)')
    a = plt.xticks(rotation=60)
    buf = BytesIO()
    fig.savefig(buf, format="png")
    st.image(buf)
    
    
    st.markdown('---')
    return None
# =======================
#         MAIN
# =======================    
    
if __name__ == '__main__':
    # extraction
    filter_recommended = st.sidebar.selectbox('What kind of houses are you interested in?',
                                      ('All houses', 'Recommended houses'))
    kpi_data = get_data('recommendations.csv')
    if filter_recommended == 'All houses':
        data = get_data('kc_house_data_full.csv')
    else:
        data = get_data('recommendations.csv')
    url = 'https://opendata.arcgis.com/datasets/83fc2e72903343aabff6de8cb445b81c_2.geojson'
    geofile = get_geofile(url)
        
    # transformation  
    data = feature_engineering(data)
    filtered_data = filters(data)
    
    # load
    kpis(kpi_data)
    try:
        plots(filtered_data)
        portfolio_density(filtered_data, geofile)
    except:
        st.error('The filters combination returned zero houses... Try another combination.')
    
#     =============================
#               ABOUT ME
#     ============================= 

    st.markdown('---')
    st.title('About the Author:')
    st.write('Hello There! :smile:')
    st.markdown('This is a Strategic Dashboard built by **Rodrigo Maranhão** as part of a solution to a fictitious real state company.')
    st.markdown('If you want to understand the context and know more about the project, please visit my [GitHub](https://github.com/rodrigomm92/king_county_house_sales) page.')
    st.write('If you are passionate about the universe of Data Science, contact with me through my [Linkedin](https://www.linkedin.com/in/rodrigomaranhaomonteiro/), or e-mail me at rodrigomaranhao.m@gmail.com')
    





