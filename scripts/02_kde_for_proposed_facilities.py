
## HERE WE ESTIMATE THE STUDENT HOUSING CLUSTERS TO PROPOSE NEW LOCATIONS FOR THE MENTAL HEALT FACILITIES AND RUN 
## A VALIDATION FOR THE EXISTING FACILITIES AND PROPOSED FACILITIES

# required modules
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import contextily as ctx
import geopandas as gpd
import pandas as pd

# Prepare the data and filter to get only students who travel > 60 mins to the existing facilities
unserved = travel_time_result[travel_time_result['travel_time'] > 60].copy()

# Error Check: Do we have enough students to cluster?
if len(unserved) < 3:
    print("Not enough unserved students to find 3 clusters. Try lowering K.")
else:
    # Get coordinates for the algorithm
    coords = unserved[['latitude', 'longitude']].values

    # RUN CLUSTERING (K=3) # fit number to your project requirement
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10).fit(coords)
    centers = kmeans.cluster_centers_ # mathematically optimal centers

    # CREATE "SEARCH ZONES" (Buffers) & Convert centers to GeoDataFrame
    df_centers = pd.DataFrame(centers, columns=['latitude', 'longitude'])
    gdf_centers = gpd.GeoDataFrame(
        df_centers, 
        geometry=gpd.points_from_xy(df_centers.longitude, df_centers.latitude), 
        crs="EPSG:4326"
    )

    # project to Metric System (Web Mercator) for the buffering viz
    gdf_centers_metric = gdf_centers.to_crs(epsg=3857)
    # Create a 1km (1000m) buffer around each point
    search_zones = gdf_centers_metric.buffer(1000) 
    # visualise the proposed locations
    fig, ax = plt.subplots(figsize=(12, 12))

    # Convert everything to Web Mercator for plotting
    unserved_web = unserved.to_crs(epsg=3857)
    facilities_web = facilities_gdf.to_crs(epsg=3857)

    # Layer 1: Unserved Students - Red Dots
    unserved_web.plot(ax=ax, color='red', alpha=0.5, markersize=20, label='Unserved Students (>60m)')

    # Layer 2: The Existing facilities - Blue Squares
    facilities_web.plot(ax=ax, color='blue', marker='s', markersize=100, label='Existing Facilities')

    # Layer 3: The Search Zones - Yellow Circles
    # We plot the boundary of the 1km zone
    search_zones.plot(ax=ax, facecolor='yellow', edgecolor='black', alpha=0.4, label='Proposed 1km Search Zone')

    # Layer 4: The Center Points (Stars)
    gdf_centers_metric.plot(ax=ax, color='black', marker='*', markersize=100, zorder=5)

    # Add Basemap
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)

    plt.title("Decentralization Strategy: 3 Proposed Service Zones", fontsize=15)
    plt.legend()
    plt.axis('off')
    plt.show()

    # 5. Print coordinates for validation
    for i, row in df_centers.iterrows():
        print(f"Zone {i+1} Center: {row['latitude']:.5f}, {row['longitude']:.5f}")

## COVERAGE VALIDATION FOR THE EXISTING LOCATION AND PROPOSED LOACTIONS
import pandas as pd
import geopandas as gpd
from r5py import TravelTimeMatrixComputer
from datetime import datetime
import os

# PREPARE THE FULL(NEW) FACILITY LIST
# Convert the 3 K-Means centers (from previous step) into a DataFrame
df_proposed = pd.DataFrame(centers, columns=['latitude', 'longitude'])
df_proposed['type'] = 'Proposed Satellite'
df_proposed['id'] = [f'Prop_{i}' for i in range(len(df_proposed))] 

# Get existing facilities (ensure columns names are consistent)
df_existing = facilities_gdf[['id', 'geometry']].copy()
df_existing['latitude'] = df_existing.geometry.y
df_existing['longitude'] = df_existing.geometry.x
df_existing['type'] = 'Existing Core'
df_existing = df_existing.drop(columns=['geometry'])
all_facilities_df = pd.concat([df_existing, df_proposed], ignore_index=True) #concantenate the facilities to one list

# Convert to GeoDataFrame for r5py
all_facilities_gdf = gpd.GeoDataFrame(
    all_facilities_df,
    geometry=gpd.points_from_xy(all_facilities_df.longitude, all_facilities_df.latitude),
    crs="EPSG:4326"
)

# Run the routing engine script again (or not if it is still active i.e you didn't close or cancel your script yet)
print("Running network Scenario with 6 Facilities...")

# Define the computer
computer_after = TravelTimeMatrixComputer(
    transport_network,
    origins=students_gdf,
    destinations=all_facilities_gdf, # <--- Now using ALL 6 locations
    departure=datetime(2025, 12, 1, 9, 0),
    transport_modes=["WALK", "TRANSIT"]
)

# Calculate
matrix_after = computer_after.compute_travel_times()

# Find min time for each student
fastest_after = matrix_after.dropna().sort_values('travel_time')
fastest_after = fastest_after.groupby('from_id').first().reset_index()

# Merge back to students
results_after = students_gdf.merge(fastest_after, left_on='id', right_on='from_id')

# Calculate Metrics
cutoff = 60
served_before = 21.57 # Your previous result
served_after = len(results_after[results_after['travel_time'] <= cutoff])
percent_after = (served_after / len(students_gdf)) * 100

print(f" IMPACT ANALYSIS")
print(f"Accessibility Before: {served_before}%")
print(f"Accessibility After:  {percent_after:.2f}%")
print(f"Improvement: +{percent_after - served_before:.2f}% points")

# Export the 3 New Locations so you can load them into ArcGIS Pro for further analysis
df_proposed.to_csv("proposed_locations_for_arcgis.csv", index=False)
print("'proposed_locations_for_arcgis.csv' saved.")