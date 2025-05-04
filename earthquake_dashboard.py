import requests
import pandas as pd
import streamlit as st
import json
from datetime import datetime

USGS_API_URL= "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/1.0_day.geojson"  #This is a directly accessible API
print(f"Data from the API: {USGS_API_URL}")


def fetch_earthquake_data(url):
    try:
        response=requests.get(url, timeout=10)
        response.raise_for_status() #if the response status isn't 200, it will jump to exception
        print("API call was successful!")
        return response.json() 
    
    except requests.exceptions.Timeout:     #To handle the timeout error 
        print("Error: Request was timed out while fetching")
        return None
    except requests.exceptions.RequestException as e:   #To handle the other errors
        print(f"Error fetching data {e}")
        return None 
    except json.JSONDecodeError:    #To handle the json error
        print("Error: Couldn't decode json response")
        return None


def process_earthquake_data(json_data):
    if not json_data or 'features' not in json_data:
        st.error("Error: No features found in earthquake data") #using st.error get pass the error message streamlit
        return None
    
    features=json_data['features']
    print(f"Processing {len(features)} earthquake features")

    earthquake_list=[]
    for feature in features:
        try:
            properties=feature.get('properties')
            geometry=feature.get('geometry', {})
            coordinates=geometry.get('coordinates',[None, None, None]) #if coordinates not found we return 3 nones

            earthquake_info={'place':properties.get('place'), 
                             'magnitude':properties.get('mag'),
                             'time_utc': pd.to_datetime(properties.get('time'),unit='ms', errors='coerce' ),
                             'url': properties.get('url'),
                             'status': properties.get('status'),
                             'type': properties.get('type'),
                             'significance':properties.get('sig'),
                             'latitude': coordinates[1],
                             'longitude': coordinates[0],
                             'depth_km': coordinates[2]   } #to_datetime takes the time in ms

            earthquake_list.append(earthquake_info)
        except Exception as e:
            print(f"Error: processing {feature.get('id', 'N/A')}- {e}")
    if not earthquake_list:
        st.warning("No earthquake data was processed")
        return None
    
    df=pd.DataFrame(earthquake_list)

    df['magnitude']=pd.to_numeric(df['magnitude'], errors='coerce') #let the magnitude is the float since magnitude unit is float
    df['significance']=pd.to_numeric(df['significance'], errors='coerce').astype('Int64')
    df['latitude']=pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude']=pd.to_numeric(df['longitude'], errors='coerce')
    df['depth_km']=pd.to_numeric(df['depth_km'], errors='coerce')

    df.dropna(subset=['time_utc', 'magnitude', 'latitude', 'longitude'], inplace=True)

    print(f"Created the Dataframe with {len(df)} after processing")

    return df



if __name__=="__main__":


    st.set_page_config(layout="wide")
    st.title("🌍 USGS Earthquake Tracker Dashboard")
    st.markdown("Displays recent earthquakes (M1.0+ in the past day) based on USGS data.")

    earthquake_json=fetch_earthquake_data(USGS_API_URL)

    if earthquake_json:
        df_earthquake=process_earthquake_data(earthquake_json)

        if df_earthquake is not None and not df_earthquake.empty:
            st.success(f"Successfully fetched and processed {len(df_earthquake)} earthquakes")

            st.header("Recent Earthquakes Map")
            st.caption("Map showing locations of recent earthquakes. Size indicates magnitude (larger = bigger).")
            map_df=df_earthquake[['latitude', 'longitude', 'magnitude']]  #we create a new df listing the columns in list of list
            map_df.dropna(subset=['latitude', 'longitude','magnitude'], inplace=True)

            if not map_df.empty:
                st.map(map_df, latitude='latitude', longitude='longitude', size='magnitude')
            else:
                st.warning("No valid coordinates data to display on map.")

            st.header("Earthquake Data Table")
            st.caption("Detailed information for recent earthquakes. Sort by clicking column headers")
            display_columns=['time_utc', 'place','magnitude', 'depth_km', 'latitude', 'longitude','significance', 'status','type', 'url']
            st.dataframe(df_earthquake[display_columns], use_container_width=True)
            
            st.sidebar.header("Summary Statistics")
            st.sidebar.metric("Total Earthquakes Displayed", len(df_earthquake) )
            st.sidebar.metric("Max Magnitude", f"{df_earthquake['magnitude'].max():.2f}")
            st.sidebar.metric("Min Magnitude", f"{df_earthquake['magnitude'].min():.2f}")
            st.sidebar.metric("Median Magnitude", f"{df_earthquake['magnitude'].median():.2f}")
        
        else:
            st.warning("Could not process the earthquake data in to Dataframe")
    else:
        st.error("Error: Fetching the json data from API")

    st.sidebar.info(f"Data fetched from {USGS_API_URL}")
    st.sidebar.write("Last fetched",pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M:%S %Z'))

