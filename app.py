import streamlit as st
import json
import httpx
from PIL import Image
from io import BytesIO
import time
from pymongo import MongoClient
import pandas as pd
import os
import numpy as np
from datetime import datetime

# MongoDB Connection (Local or Atlas)
MONGO_URI = "mongodb://localhost:27017/"  # Replace with your MongoDB credentials
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["SocialScan"]  # Database name
collection = db["users"]  # Collection name

# Define the HTTP client
client = httpx.Client(
    headers={
        "x-ig-app-id": "936619743392459",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "/",
        
    }
)

# ===================== INSTAGRAM SCRAPER FUNCTIONS =====================
def scrape_user(username: str):
    """Scrape Instagram user's data and extract relevant info, including all available images, captions, and comments."""
    try:
        result = client.get(f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}")

        if result.status_code != 200:
            return f"Failed to retrieve data. Status code: {result.status_code}", []

        try:
            data = json.loads(result.content)
        except json.JSONDecodeError:
            return "Error decoding JSON response from the server.", []

        user_info = data.get("data", {}).get("user", {})
        if not user_info:
            return "User not found or unable to retrieve data.", []

        # Extract User Details
        user = {
            "Username": user_info.get("username", "N/A"),
            "Full Name": user_info.get("full_name", "N/A"),
            "ID": user_info.get("id", "N/A"),
            "Category": user_info.get("category_name", "N/A"),
            "Business Category": user_info.get("business_category_name", "N/A"),
            "Phone": user_info.get("business_phone_number", "N/A"),
            "Email": user_info.get("business_email", "N/A"),
            "Biography": user_info.get("biography", "N/A"),
            "Bio Links": [link.get("url") for link in user_info.get("bio_links", []) if link.get("url")],
            "Homepage": user_info.get("external_url", "N/A"),
            "Followers": f"{user_info.get('edge_followed_by', {}).get('count', 0):,}",
            "Following": f"{user_info.get('edge_follow', {}).get('count', 0):,}",
            "Facebook ID": user_info.get("fbid", "N/A"),
            "Is Private": user_info.get("is_private", "N/A"),
            "Is Verified": user_info.get("is_verified", "N/A"),
            "Profile Image": user_info.get("profile_pic_url_hd", "N/A"),
            "Video Count": user_info.get("edge_felix_video_timeline", {}).get("count", 0),
            "Image Count": user_info.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "Saved Count": user_info.get("edge_saved_media", {}).get("count", 0),
            "Collections Count": user_info.get("edge_saved_media", {}).get("count", 0),
            "Related Profiles": [profile.get("node", {}).get("username", "N/A") for profile in user_info.get("edge_related_profiles", {}).get("edges", [])],
        }

        # Extract Images, Captions, and Comments
        images = user_info.get("edge_owner_to_timeline_media", {}).get("edges", [])
        image_info = []

        for image in images:
            image_node = image.get("node", {})
            comments = []
            if image_node.get("edge_media_to_comment", {}).get("count", 0) > 0:
                comments_query = client.get(f"https://i.instagram.com/api/v1/media/{image_node.get('id')}/comments/")
                if comments_query.status_code == 200:
                    comments_data = comments_query.json()
                    comments = [comment.get("text", "") for comment in comments_data.get("comments", [])]

            image_info.append({
                "ID": image_node.get("id", "N/A"),
                "Source": image_node.get("display_url", "N/A"),
                "Likes": image_node.get("edge_liked_by", {}).get("count", 0),
                "Caption": image_node.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", "N/A"),
                "Comments": comments,
            })

        return user, image_info
    except Exception as e:
        return f"An error occurred: {e}", []

def fetch_image(url):
    """Fetch image from URL and return PIL Image object, or a placeholder if failed."""
    try:
        response = client.get(url, timeout=5)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception:
        pass  # Handle errors silently

    # Return a placeholder image if loading fails
    return Image.open("placeholder.png")  # Ensure placeholder.png exists

def save_to_mongo(user_info, images):
    """Save scraped data to MongoDB."""
    if isinstance(user_info, str):  # If there's an error message, don't save
        st.error(user_info)
        return False

    user_data = {
        "user_info": user_info,
        "images": images,
        "timestamp": time.time(),
        "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Check if user already exists in the database
    existing_user = collection.find_one({"user_info.Username": user_info["Username"]})
    if existing_user:
        st.warning("User data already exists in MongoDB. Updating record.")
        collection.update_one(
            {"user_info.Username": user_info["Username"]},
            {"$set": user_data}
        )
    else:
        collection.insert_one(user_data)
        st.success("Data successfully saved to MongoDB")
    
    return True

def display_user_info(user_info):
    """Display the user's information"""
    st.subheader("User Information")
    if isinstance(user_info, str):
        st.error(user_info)
    else:
        for key, value in user_info.items():
            st.write(f"{key}:** {value}")
        
        if user_info.get("Profile Image"):
            try:
                response = client.get(user_info.get("Profile Image"))
                img = Image.open(BytesIO(response.content))
                st.image(img, caption="Profile Picture", use_container_width=True)
            except Exception as e:
                st.error(f"Error loading profile image: {e}")

def display_media_grid(media_list, columns=3):
    """Display images in a responsive Instagram-style grid with Post ID, Likes, Captions, and Comments."""
    st.subheader("User's Latest Posts")

    if not media_list:
        st.warning("No images found.")
        return

    rows = [media_list[i:i+columns] for i in range(0, len(media_list), columns)]  # Split into rows
    
    for row in rows:
        cols = st.columns(columns)  # Create columns dynamically

        for idx, media in enumerate(row):
            if idx < len(row):
                with cols[idx]:  # Place each image in its respective column
                    img = fetch_image(media["Source"])  # Fetch the image
                    st.image(img, use_container_width=True)  # Ensure it fits the column width
                    st.write(f"❤ {media['Likes']} Likes**")
                    st.caption(f"📌 Post ID: {media['ID']}")
                    
                    # Display caption in an expander
                    with st.expander("View Caption"):
                        st.write(f"{media['Caption']}")

                    # Display comments in an expander
                    if media["Comments"]:
                        with st.expander(f"View Comments ({len(media['Comments'])})"):
                            for comment in media["Comments"]:
                                st.write(f"- {comment}")

def get_saved_usernames():
    """Get list of usernames saved in MongoDB."""
    try:
        users = collection.find({}, {"user_info.Username": 1, "scrape_date": 1})
        return [(user.get("user_info", {}).get("Username"), 
                 user.get("scrape_date", "Unknown date")) 
                for user in users if "user_info" in user and "Username" in user["user_info"]]
    except Exception as e:
        st.error(f"Error fetching saved usernames: {e}")
        return []

def load_saved_user(username):
    """Load a previously saved user from MongoDB."""
    try:
        user_data = collection.find_one({"user_info.Username": username})
        if user_data:
            return user_data.get("user_info"), user_data.get("images", [])
        else:
            return f"User {username} not found in database.", []
    except Exception as e:
        return f"Error loading user data: {e}", []

def export_user_data_to_csv(username):
    """Export user data to CSV file."""
    try:
        user_data = collection.find_one({"user_info.Username": username})
        if not user_data:
            return False, f"User {username} not found in database."
        
        # Flatten user info
        flat_user = {"user_info." + k: v for k, v in user_data.get("user_info", {}).items()}
        
        # Flatten image data
        for i, image in enumerate(user_data.get("images", [])):
            for k, v in image.items():
                if k != "Comments":  # Skip comments array to keep it simple
                    flat_user[f"images[{i}].{k}"] = v
        
        # Convert to DataFrame and export
        df = pd.DataFrame([flat_user])
        filename = f"{username}_data.csv"
        df.to_csv(filename, index=False)
        
        return True, filename
    except Exception as e:
        return False, f"Error exporting data: {e}"

# ===================== ANALYSIS FUNCTIONS =====================
def analyze_behavior(username):
    """Analyze behavior of a specific Instagram user based on loaded data."""
    # Load data
    try:
        DATA_PATH = 'dataset1_train.csv'
        data = pd.read_csv(DATA_PATH)

        # Debug: Print unique usernames to check what's available
        st.write(f"Debug: Available usernames: {data['user_info.Username'].unique()}")
        
        # Debug: Print the username we're trying to find
        st.write(f"Debug: Looking for username: {username}")

        # Select relevant columns
        columns_to_keep = ['user_info.Username', 'user_info.Category', 'user_info.Related Profiles'] + \
                          [f'images[{i}].Likes' for i in range(12)] + [f'images[{i}].Caption' for i in range(12)]

        # Check if all columns exist in the dataset
        existing_columns = [col for col in columns_to_keep if col in data.columns]
        if len(existing_columns) < len(columns_to_keep):
            missing_columns = set(columns_to_keep) - set(existing_columns)
            st.warning(f"Some columns are missing in the dataset: {missing_columns}")
        
        # Use only columns that exist in the dataset
        data = data[existing_columns]

        # Handle missing values and convert data types
        for i in range(12):
            likes_col = f'images[{i}].Likes'
            caption_col = f'images[{i}].Caption'
            
            if likes_col in data.columns:
                data[likes_col] = pd.to_numeric(data[likes_col], errors='coerce').fillna(0)
            
            if caption_col in data.columns:
                data[caption_col] = data[caption_col].fillna("")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

    # Filter data for the selected user - making sure to check case insensitivity and whitespace
    # Debug: show the filtering process
    st.write(f"Total records before filtering: {len(data)}")
    
    # Clean username values for comparison
    data['cleaned_username'] = data['user_info.Username'].str.strip().str.lower()
    cleaned_input_username = username.strip().lower()
    
    user_data = data[data['cleaned_username'] == cleaned_input_username]
    
    st.write(f"Records found after filtering: {len(user_data)}")
    
    if user_data.empty:
        st.error(f"No data found for user: {username}")
        return None
    
    # Fetch user category and related profiles
    category = user_data['user_info.Category'].iloc[0] if 'user_info.Category' in user_data.columns else "Unknown"
    related_profiles = user_data['user_info.Related Profiles'].iloc[0] if 'user_info.Related Profiles' in user_data.columns else "None"
    
    # Extract likes and captions
    likes_and_captions = []
    for i in range(12):
        likes_column = f'images[{i}].Likes'
        caption_column = f'images[{i}].Caption'
        
        # Check if the columns exist in the dataset
        if likes_column in user_data.columns and caption_column in user_data.columns:
            likes = user_data[likes_column].iloc[0]
            caption = user_data[caption_column].iloc[0]
            
            # Ensure likes are numeric and captions are strings
            if pd.notna(likes) and pd.notna(caption):
                likes_and_captions.append((int(likes), str(caption)))
    
    if not likes_and_captions:
        st.warning("No likes and captions data found for this user")
        return None
    
    # Calculate average likes
    avg_likes = sum(like for like, _ in likes_and_captions) / len(likes_and_captions)
    
    # Sort likes and captions in descending order of likes
    sorted_likes_captions = sorted(likes_and_captions, key=lambda x: x[0], reverse=True)

    # Remove debug information before returning the results
    # st.write("Debug information complete. Returning analysis results.")
    
    return {
        'category': category,
        'related_profiles': related_profiles,
        'avg_likes': avg_likes,
        'sorted_likes_captions': sorted_likes_captions
    }

def generate_prompt(username, query):
    """Generate a prompt for the LLM based on user behavior analysis."""
    behavior = analyze_behavior(username)
    if not behavior:
        return "No data available for the selected user."
    
    prompt = f"Generate a response for {username}, a {behavior['category']} influencer. "
    prompt += f"Related profiles: {behavior['related_profiles']}. "
    prompt += f"Top performing captions include: {', '.join([caption for _, caption in behavior['sorted_likes_captions'][:5]])}. "
    prompt += f"Average engagement score: {behavior['avg_likes']:.2f}. Query: {query}"
    
    try:
        # Note: In the original code, there was a model.generate_content() call here
        # Since you didn't provide the model configuration, I'll return the prompt for now
        # Uncomment and modify the code below when you have your LLM model configured
        
        # response = model.generate_content(prompt)
        # return response.text
        
        # For now, just return the prompt as a placeholder
        return f"LLM Query: {prompt}\n\n[LLM response would appear here - model not configured]"
    except Exception as e:
        return f"❌ Error generating content: {e}"

# ===================== STREAMLIT APP =====================
def main():
    st.set_page_config(
        page_title="SocialScan",
        page_icon="📱",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add application title and description
    st.title("📱 SocialScan")
    st.markdown("### A comprehensive social media analysis tool")
    
    # Create a sidebar for navigation
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.radio(
        "Choose a module:",
        ["Instagram Scraper", "User Behavior Analysis"]
    )
    
    # Instagram Scraper Module
    if app_mode == "Instagram Scraper":
        st.header("Instagram Profile Scraper")
        
        # Add sub-navigation for different scraping options
        scraper_option = st.radio(
            "Select scraping option:",
            ["New Scraper", "Saved Scraper", "Batch Scraper"],
            horizontal=True
        )
        
        # 1. New Scraper Option (Single user scraping - original functionality)
        if scraper_option == "New Scraper":
            st.subheader("Scrape a Single Instagram Profile")
            st.markdown("Enter an Instagram username to scrape their profile data and posts.")
            
            username = st.text_input("Enter the Instagram username", placeholder="Username")
            
            if st.button("Scrape Data"):
                if username:
                    with st.spinner(f"Scraping data for {username}..."):
                        user_info, images = scrape_user(username)
                    
                    # Save to MongoDB
                    save_to_mongo(user_info, images)
                    
                    # Display user info and images
                    display_user_info(user_info)
                    display_media_grid(images)
                else:
                    st.error("Please enter a valid username")
        
        # 2. Saved Scraper Option (View previously scraped profiles)
        elif scraper_option == "Saved Scraper":
            st.subheader("View Saved Instagram Profiles")
            st.markdown("Select a previously scraped Instagram profile to view data.")
            
            # Get list of saved usernames
            saved_users = get_saved_usernames()
            
            if not saved_users:
                st.warning("No saved profiles found. Use the 'New Scraper' option to scrape profiles first.")
            else:
                # Format usernames with scrape dates for selection
                user_options = [f"{username} (Scraped: {date})" for username, date in saved_users]
                selected_option = st.selectbox("Select a saved profile:", user_options)
                
                if selected_option:
                    # Extract username from selected option
                    selected_username = selected_option.split(" (Scraped:")[0]
                    
                    # Add action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Load Profile Data"):
                            with st.spinner(f"Loading saved data for {selected_username}..."):
                                user_info, images = load_saved_user(selected_username)
                                
                                # Display user info and images
                                display_user_info(user_info)
                                display_media_grid(images)
                    
                    with col2:
                        if st.button("Export to CSV"):
                            with st.spinner(f"Exporting data for {selected_username}..."):
                                success, result = export_user_data_to_csv(selected_username)
                                if success:
                                    st.success(f"Data exported successfully to {result}")
                                    
                                    # Create download button for the CSV
                                    with open(result, 'rb') as file:
                                        st.download_button(
                                            label="Download CSV",
                                            data=file,
                                            file_name=result,
                                            mime="text/csv"
                                        )
                                else:
                                    st.error(result)
        
        # 3. Batch Scraper Option (Scrape multiple profiles at once)
        elif scraper_option == "Batch Scraper":
            st.subheader("Batch Scrape Multiple Instagram Profiles")
            st.markdown("Enter multiple Instagram usernames to scrape data in batch.")
            
            # Text area for multiple usernames
            usernames_input = st.text_area(
                "Enter Instagram usernames (one per line):",
                placeholder="username1\nusername2\nusername3"
            )
            
            # Process rate limit
            rate_limit = st.slider(
                "Processing delay between requests (seconds)",
                min_value=1,
                max_value=10,
                value=3,
                help="Higher values reduce the risk of being rate-limited by Instagram"
            )
            
            # Session state initialization for storing successful profiles
            if 'successful_profiles' not in st.session_state:
                st.session_state.successful_profiles = []
            
            if st.button("Start Batch Scraping"):
                if usernames_input:
                    # Parse usernames
                    usernames = [u.strip() for u in usernames_input.split("\n") if u.strip()]
                    
                    if not usernames:
                        st.error("No valid usernames found.")
                    else:
                        # Create a progress bar
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Results containers
                        successful = []
                        failed = []
                        
                        # Process each username
                        for i, username in enumerate(usernames):
                            status_text.text(f"Processing {i+1}/{len(usernames)}: {username}...")
                            
                            try:
                                # Scrape user data
                                user_info, images = scrape_user(username)
                                
                                # Save to MongoDB if successful
                                if not isinstance(user_info, str) and save_to_mongo(user_info, images):
                                    successful.append(username)
                                else:
                                    failed.append((username, "Failed to save data"))
                            except Exception as e:
                                failed.append((username, str(e)))
                            
                            # Update progress
                            progress_bar.progress((i + 1) / len(usernames))
                            
                            # Sleep to avoid rate limiting
                            time.sleep(rate_limit)
                        
                        # Store successful profiles in session state
                        st.session_state.successful_profiles = successful
                        
                        # Display results
                        st.success(f"✅ Batch processing complete! Successfully scraped {len(successful)} profiles.")
                        
                        if successful:
                            with st.expander("Successfully scraped profiles"):
                                for username in successful:
                                    st.write(f"- {username}")
                        
                        if failed:
                            with st.expander("Failed to scrape profiles"):
                                for username, error in failed:
                                    st.write(f"- {username}: {error}")
            
            # Display data for successfully scraped profiles
            if st.session_state.successful_profiles:
                st.subheader("View Scraped Profile Data")
                
                # Option 1: View individual profile
                profile_to_view = st.selectbox(
                    "Select a profile to view:",
                    st.session_state.successful_profiles
                )
                
                if st.button("View Selected Profile"):
                    with st.spinner(f"Loading data for {profile_to_view}..."):
                        user_info, images = load_saved_user(profile_to_view)
                        display_user_info(user_info)
                        display_media_grid(images)
                
                # Option 2: View all profiles in expanders
                if st.checkbox("Show all scraped profiles data"):
                    for username in st.session_state.successful_profiles:
                        with st.expander(f"Profile: {username}"):
                            with st.spinner(f"Loading data for {username}..."):
                                user_info, images = load_saved_user(username)
                                display_user_info(user_info)
                                display_media_grid(images)
    
    # User Behavior Analysis Module
    elif app_mode == "User Behavior Analysis":
        st.header("📊 User Behavior Analysis")
        st.markdown("Analyze social media behavior and engagement patterns.")
        
        # Check if dataset exists
        if not os.path.exists('dataset1_train.csv'):
            st.error("Dataset not found. Please make sure 'dataset1_train.csv' is in the same directory as this script.")
        else:
            try:
                data = pd.read_csv('dataset1_train.csv')
                usernames = data['user_info.Username'].unique()
                
                # Select username
                selected_user = st.selectbox("👤 Select a username", usernames)
                
                # Input for user query
                query = st.text_input("💬 Ask about the user behavior:")
                
                if st.button("🚀 Analyze"):
                    behavior = analyze_behavior(selected_user)
                    if behavior:
                        # Display user behavior analysis
                        st.write("### 🔎 User Behavior Analysis:")
                        st.write(f"*Category:* {behavior['category']}")
                        st.write(f"*Related Profiles:* {behavior['related_profiles']}")
                        st.write(f"*Average Engagement Score:* {behavior['avg_likes']:.2f}")
                        
                        # Replace the table display code in the User Behavior Analysis section

                        # And replace it with:
                        st.write("❤ *Likes and Captions (Sorted by Likes):*")
                        likes_captions_df = pd.DataFrame(behavior['sorted_likes_captions'], columns=["Likes", "Caption"])

                        # Use st.dataframe instead of st.table with column configuration
                        st.dataframe(
                            likes_captions_df,
                            column_config={
                                "Likes": st.column_config.NumberColumn(
                                    "Likes ❤",
                                    width="small",  # You can use "small", "medium", "large" or specific pixel value like "150px"
                                    format="%d"  # Format as integer
                                ),
                                "Caption": st.column_config.TextColumn(
                                    "Caption 📝",
                                    width="large"
                                )
                            },
                            hide_index=True
                        )
                        
                        # Generate LLM response if query is provided
                        if query:
                            st.write("### 🤖 LLM Response:")
                            result = generate_prompt(selected_user, query)
                            st.write(result)
                    else:
                        st.write("⚠ No data available for the selected user.")
            except Exception as e:
                st.error(f"Error loading the dataset: {e}")

if __name__ == "__main__":
    main()