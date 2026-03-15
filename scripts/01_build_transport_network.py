## Required modules
import geopandas as gpd
import pandas as pd
from r5py import TransportNetwork, TravelTimeMatrixComputer
from datetime import datetime
print("Libraries imported successfully!")

## STEP 1 - PATH DEFINITION
# The Street Network (OSM)
# Make sure this matches the file name in your 'data' folder exactly.
osm_file = os.path.join("data", "oberbayern-251203.osm.pbf")

# The Public Transport Schedule (GTFS)
# r5py requires this to be a LIST [...] even if it's just one file.
gtfs_file = [os.path.join("data", "gesamt_gtfs.zip")] 

# This is a safety check. It will tell you if the file path is wrong before crashing.
if not os.path.exists(osm_file):
    print(f" ERROR: Could not find OSM file at: {osm_file}")
else:
    print(f" Found OSM file: {osm_file}")

if not os.path.exists(gtfs_file[0]):
    print(f" ERROR: Could not find GTFS file at: {gtfs_file[0]}")
else:
    print(f" Found GTFS file: {gtfs_file[0]}")

## STEP 2 - LOADING PRIMARY DATA
# Load Student Survey Data
survey_df = pd.read_csv(os.path.join("data", "student_priv.csv"))
survey_df['type'] = "Private/Survey" # Add a tag 

# Load Studentwerk Halls Data
# Make sure this CSV also has 'latitude' and 'longitude' columns!
halls_df = pd.read_csv(os.path.join("data", "studentenwerk_halls.csv"))
halls_df['type'] = "Studentenwerk Hall" # Add a tag

# Combine them into one big list
all_origins = pd.concat([survey_df, halls_df], ignore_index=True) #concatenation to stack the csv on top of each other

# Convert the new list to GeoDataFrame
students_gdf = gpd.GeoDataFrame(
    all_origins, 
    geometry=gpd.points_from_xy(all_origins.longitude, all_origins.latitude),
    crs="EPSG:4326"
)
students_gdf['id'] = students_gdf.index 

print(f"Total Origins: {len(students_gdf)} ({len(survey_df)} Survey + {len(halls_df)} Halls)")
# Add mental health facilities layer/reference layer of choice
facilities_df = pd.read_csv(os.path.join("data", "facilities.csv"))

# Convert to Spatial Layer (GeoDataFrame)
facilities_gdf = gpd.GeoDataFrame(
    facilities_df,
    geometry=gpd.points_from_xy(facilities_df.longitude, facilities_df.latitude),
    crs="EPSG:4326"
)
# Add an ID column (Crucial for the analysis to track which facility is which)
facilities_gdf['id'] = facilities_gdf.index

print(f"Loaded {len(facilities_gdf)} facilities.")

### STEP 3- NETWORK CREATION
## Run Routing engine with the TravelTimeMatrixComputer
transport_network = TransportNetwork(osm_file, gtfs_file) #temporary file creation in working folder
print("Transport Network built successfully.")

## STEP 4 - NETWORK ANALYSIS
# Monday morning at 9:00 AM (Rush hour scenario)
departure_time = datetime(2025, 12, 8, 9, 0) #8th December, 2025
computer = TravelTimeMatrixComputer(
    transport_network,
    origins=students_gdf,
    destinations=facilities_gdf,
    departure=departure_time,
    transport_modes=["WALK", "TRANSIT"] # This enables Public Transport
)
print("Computing travel times...")
travel_time_matrix = computer.compute_travel_times()
print("Calculation done!")
print(travel_time_matrix.head())

## STEP 5 - NETWORK ANALYSIS FILTERING AND EXPORT
# dropna() removes rows where travel is impossible.
fastest_trips = travel_time_matrix.dropna().sort_values('travel_time')
fastest_trips = fastest_trips.groupby('from_id').first().reset_index()

# Add the Student Info back so you have coordinates
final_results = students_gdf.merge(fastest_trips, left_on='id', right_on='from_id')

# Calculating statistics of the analysis
cutoff_minutes = 60
accessible_count = len(final_results[final_results['travel_time'] <= cutoff_minutes])
total_students = len(students_gdf)
percent_access = (accessible_count / total_students) * 100

print(f"RESULTS")
print(f"Total Students: {total_students}")
print(f"Students within {cutoff_minutes} mins (Public Transport): {accessible_count}")
print(f"Percentage Accessible: {percent_access:.2f}%")

# export result as csv
final_results.to_csv("final_pt_accessibility.csv", index=False)
print("Saved to 'final_pt_accessibility.csv'")