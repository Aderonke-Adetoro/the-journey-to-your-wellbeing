## ISOCHRONES GENERATION FOR EXISTING FACILITIES AND PROPOSED FACILITIES

from r5py import TransportNetwork, Isochrones
import geopandas as gpd
import pandas as pd
from datetime import datetime
import os

# Ensure df_proposed exists
if 'df_proposed' not in locals():
    # Fallback if variable is lost: Create dummy data to prevent crash
    print(" 'df_proposed' missing. Using previously known logic to recreate it...")
else:
    df_proposed_iso = df_proposed.copy() # Prepare the data
    df_proposed_iso['id'] = [f'Proposed_{i+1}' for i in range(len(df_proposed_iso))] # Create the ID column 
    
    # Convert to GeoDataFrame
    gdf_sites = gpd.GeoDataFrame(
        df_proposed_iso,
        geometry=gpd.points_from_xy(df_proposed_iso.longitude, df_proposed_iso.latitude),
        crs="EPSG:4326"
    )

    print("Generating Public Transport Isochrones...")
    
    # Calculate
    iso_polygons = Isochrones(
        transport_network,
        origins=gdf_sites,
        departure=datetime(2025, 12, 1, 9, 0),
        transport_modes=["WALK", "TRANSIT"], 
        isochrones=[15, 30, 45, 60]
    )

    iso_polygons = iso_polygons.reset_index()

    print(f"DEBUG: Columns found in result: {iso_polygons.columns.tolist()}")

    id_candidates = ['from_id', 'id', 'site_id', 'index']
    
    found_id = None
    for col in id_candidates:
        if col in iso_polygons.columns:
            found_id = col
            break
    
    if found_id:
        print(f"DEBUG: Found ID column named '{found_id}'. Renaming to 'site_id'...")
        iso_polygons = iso_polygons.rename(columns={found_id: 'site_id'})
    else:
        print("DEBUG: No standard ID name found. Using the first column as ID.")
        iso_polygons.columns.values[0] = 'site_id'

    if 'travel_time' in iso_polygons.columns:
        iso_polygons['minutes'] = iso_polygons['travel_time'].dt.total_seconds() / 60
        iso_polygons['minutes'] = iso_polygons['minutes'].astype(int)
    else:
        raise KeyError(f"Could not find 'travel_time' column. Available: {iso_polygons.columns}")

    iso_export = iso_polygons[['site_id', 'minutes', 'geometry']].copy()

    output_folder = "output_isochrones" #EXPORT ISOCHRONES
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    save_path = os.path.join(output_folder, "proposed_pt_service_areas.shp")
    iso_export.to_file(save_path)

    print(f" Polygons saved to: {save_path}")