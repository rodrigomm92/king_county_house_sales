#streamlit run teste_streamlit.py # linkar a pagina streamlit com o arquivo
import numpy  as np
import pandas as pd
import seaborn as sns
import geopandas
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
import matplotlib.pyplot as plt
from datetime import datetime
from PIL import Image
from io import BytesIO

st.set_page_config(layout='wide') #centered ou wide
st.sidebar.title('Strategic Dashboard')
image = Image.open('banner.png')
st.sidebar.image(image,use_column_width=True,caption='Find what you are looking for!')
st.sidebar.title('Filter Options')

st.title('King County House Sales Dashboard')
# st.markdown('Welcome to House Rocket Data Analysis')

@st.cache(allow_output_mutation=True)
def get_data(path):
    data = pd.read_csv(path, parse_dates=['date'])
    return data

@st.cache(allow_output_mutation=True)
def get_geofile(url):
    geofile = geopandas.read_file(url)
    return geofile

def filters(data):
    filter_yr_built = st.sidebar.slider('Year Built', data['yr_built'].min(), data['yr_built'].max(),
                                       (data['yr_built'].min()+15, data['yr_built'].max()-15))

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

    return filtered_data


def feature_engineering(aux2):
    # Creating feature 'renovated'
    aux2['renovated'] = aux2['yr_renovated'].apply(lambda x: 1 if x > 0 else 0)
                
    # Creating feature year_month
    aux2['year_month'] = aux2['date'].dt.strftime('%Y-%m')
                
    # Creating feature year_week
    aux2['year_week'] = aux2['date'].dt.strftime('%Y-%U')
                

    return aux2


def portfolio_density(data, geofile):
    st.title('Region Overview')
    with st.spinner('Loading map...'):
        c1, c2 = st.columns((1, 1))
        c1.header('Portfolio Density')
 
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
#     ==============
#     Year_Month Plot
#     ==============
    # Aggregating features
    count_year_month = aux2[['year_month','price']].groupby('year_month').count().reset_index()
    average_year_month = aux2[['year_month','price']].groupby('year_month').mean().reset_index()

    # Plotting
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
    
#     ==============
#     Year_Week Plot
#     ==============
    # Aggregating features
    sales_week = aux2[['price', 'year_week']].groupby('year_week').sum().reset_index()
    average_sales = aux2[['price', 'year_week']].groupby('year_week').sum()['price'].mean()

    # Plotting
    fig = plt.figure( figsize=(8, 6) )
    plt.axhline( average_sales, linestyle='--', label='Average')
    ax1 = sns.lineplot(data=sales_week.sort_values('year_week'), x='year_week', y='price', ci=None)
    std_font(ax1, 'Sum of House sales over the weeks', '', 'Price (US$)')
    a = plt.xticks(rotation=60)
    buf = BytesIO()
    fig.savefig(buf, format="png")
    st.image(buf)

if __name__ == '__main__':
    # ETL
    # extraction
    filter_recommended = st.sidebar.selectbox('What kind of houses are you interested in?',
                                      ('All houses', 'Recommended houses'))
    if filter_recommended == 'All houses':
        data = get_data('kc_house_data.csv')
    else:
        data = get_data('recommendations.csv')
    url = 'https://opendata.arcgis.com/datasets/83fc2e72903343aabff6de8cb445b81c_2.geojson'
    geofile = get_geofile(url)
        
    # transformation  
    data = feature_engineering(data)
    filtered_data = filters(data)
    try:
        plots(filtered_data)
        portfolio_density(filtered_data, geofile)
    except:
        st.error('The filters combination returned zero houses... Try another combination.')
    
    
    # -----------------
    
# --------------------  



