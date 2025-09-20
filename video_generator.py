import os
import io
import numpy as np
from PIL import Image
import imageio
import cairosvg
import base64
import random

# Video dimensions - more banner-like (16:9 but can adjust)
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FONT_SIZE = 72  # Larger for banner effect

def image_to_base64(image_path):
    """Convert image to base64 for embedding in SVG"""
    try:
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            # Detect image format
            if image_path.lower().endswith('.png'):
                return f"data:image/png;base64,{img_base64}"
            elif image_path.lower().endswith(('.jpg', '.jpeg')):
                return f"data:image/jpeg;base64,{img_base64}"
            else:
                return f"data:image/png;base64,{img_base64}"
    except Exception:
        return None

def typing_svg_frame(text, chars_visible, text_color="#00FF41", bg_image=None, overlay_opacity=0.7):
    """Generate SVG frame for terminal-banner typing animation"""
    
    # Create background
    background = ""
    if bg_image and os.path.exists(bg_image):
        # Convert image to base64 for proper embedding
        img_data = image_to_base64(bg_image)
        if img_data:
            background += f'<image href="{img_data}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice"/>'
        else:
            background += '<rect width="100%" height="100%" fill="#1a1a2e"/>'  # Dark fallback
        background += f'<rect width="100%" height="100%" fill="black" fill-opacity="{overlay_opacity}"/>'
    else:
        background += '<rect width="100%" height="100%" fill="#0f0f23"/>'  # Dark background
    
    # Banner-style design elements
    banner_height = 140  # Reduced height for sleeker look
    banner_y = (VIDEO_HEIGHT - banner_height) // 2
    
    # Semi-transparent banner background for better text visibility
    banner_bg = f'<rect x="0" y="{banner_y}" width="100%" height="{banner_height}" fill="black" fill-opacity="0.4" stroke="#00FF41" stroke-width="2"/>'
    
    # Calculate positioning for terminal-style left alignment within banner
    left_margin = 150  # More space from left edge
    text_y = VIDEO_HEIGHT // 2  # Center vertically
    
    # Build visible text (only show characters that should be typed so far)
    visible_text = text[:chars_visible]
    
    # Add cursor effect (blinking cursor after last typed character)
    cursor = "█" if chars_visible < len(text) else ""  # Block cursor
    display_text = visible_text + cursor
    
    # Add some decorative elements for banner feel
    decorative_elements = ""
    if chars_visible > 0:  # Only show decorations after typing starts
        # Left decoration
        decorative_elements += f'<text x="60" y="{text_y}" font-family="Courier New, monospace" font-size="48px" fill="{text_color}" text-anchor="start" dominant-baseline="middle">►</text>'
        # Right decoration (only when text is complete)
        if chars_visible >= len(text):
            text_width_estimate = len(visible_text) * 43  # Rough estimate
            right_x = left_margin + text_width_estimate + 50
            decorative_elements += f'<text x="{right_x}" y="{text_y}" font-family="Courier New, monospace" font-size="48px" fill="{text_color}" text-anchor="start" dominant-baseline="middle">◄</text>'
    
    # Terminal-style positioning with banner aesthetics
    svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{VIDEO_WIDTH}" height="{VIDEO_HEIGHT}" viewBox="0 0 {VIDEO_WIDTH} {VIDEO_HEIGHT}">
    <defs>
        <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge> 
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>
    {background}
    {banner_bg}
    {decorative_elements}
    <text x="{left_margin}" y="{text_y}" 
          font-family="Courier New, Consolas, Monaco, monospace" 
          font-size="{FONT_SIZE}px" 
          fill="{text_color}" 
          text-anchor="start" 
          dominant-baseline="middle"
          font-weight="bold"
          filter="url(#glow)">
        {display_text}
    </text>
</svg>"""
    
    return svg

def typing_to_mp4(text, output_file="typing.mp4", fps=6, hold_end=30, bg_image=None, text_color="#00FF41", verbose=False):
    """Create terminal-banner typing animation video"""
    
    if verbose:
        print(f"Creating animation for: '{text}'")
    
    if bg_image and not os.path.exists(bg_image):
        if verbose:
            print(f"Warning: Background image '{bg_image}' not found!")
        bg_image = None
    
    frames = []
    
    # Add a brief pause at the start (blank banner) - just 500ms
    pause_frames = max(1, int(fps * 0.5))  # 0.5 seconds = 500ms
    for _ in range(pause_frames):
        svg = typing_svg_frame(text, 0, text_color=text_color, bg_image=bg_image)
        try:
            png_bytes = cairosvg.svg2png(
                bytestring=svg.encode("utf-8"), 
                output_width=VIDEO_WIDTH,
                output_height=VIDEO_HEIGHT,
                dpi=96
            )
            img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            frames.append(np.array(img))
        except Exception as e:
            if verbose:
                print(f"Error generating initial frame: {e}")
    
    # Generate frames for typing animation
    for i in range(1, len(text) + 1):
        try:
            svg = typing_svg_frame(text, i, text_color=text_color, bg_image=bg_image)
            
            # Convert SVG to PNG
            png_bytes = cairosvg.svg2png(
                bytestring=svg.encode("utf-8"), 
                output_width=VIDEO_WIDTH,
                output_height=VIDEO_HEIGHT,
                dpi=96
            )
            
            # Convert to PIL Image and then numpy array
            img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            frames.append(np.array(img))
            
            if verbose and i % 5 == 0:
                print(f"Generated frame {i}/{len(text)}")
            
        except Exception as e:
            if verbose:
                print(f"Error generating frame {i}: {e}")
            continue
    
    if not frames:
        raise Exception("No frames were generated successfully")
    
    # Create final frame without cursor but with decorations
    try:
        final_svg = typing_svg_frame(text, len(text), text_color=text_color, bg_image=bg_image)
        # Remove cursor from final frame
        final_svg = final_svg.replace("█", "")
        
        png_bytes = cairosvg.svg2png(
            bytestring=final_svg.encode("utf-8"),
            output_width=VIDEO_WIDTH,
            output_height=VIDEO_HEIGHT,
            dpi=96
        )
        final_frame = np.array(Image.open(io.BytesIO(png_bytes)).convert("RGB"))
        
        # Hold final frame
        for _ in range(hold_end):
            frames.append(final_frame)
            
    except Exception as e:
        if verbose:
            print(f"Warning: Could not create final frame: {e}")
        for _ in range(hold_end):
            frames.append(frames[-1])
    
    if verbose:
        print(f"Total frames: {len(frames)}")
        print(f"Creating video: {output_file}")
    
    # Create video with better quality settings
    try:
        writer = imageio.get_writer(
            output_file, 
            fps=fps, 
            codec="libx264", 
            quality=9,  # Higher quality
            ffmpeg_params=[
                "-pix_fmt", "yuv420p",
                "-preset", "slow",  # Better compression
                "-crf", "18"  # High quality
            ]
        )
        
        for i, frame in enumerate(frames):
            writer.append_data(frame)
        
        writer.close()
        if verbose:
            print(f"Video saved as: {output_file}")
        
    except Exception as e:
        if verbose:
            print(f"Error creating video: {e}")
        raise
    
    return output_file

def cleanup_temp_files(*file_paths):
    """Clean up temporary files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass  # Silently ignore cleanup errors

def create_welcome_video(username, output_file="welcome.mp4", bg_image=None, cleanup=True, verbose=False):
    """
    Main function for bot usage - creates welcome video and optionally cleans up
    
    Args:
        username (str): Username to welcome
        output_file (str): Output video filename
        bg_image (str): Path to background image (optional)
        cleanup (bool): Whether to clean up temporary files
        verbose (bool): Whether to print progress messages
    
    Returns:
        str: Path to created video file
    """
    text = f"Welcome {username}!"
    temp_files = []

    color = ["#00FF41", "#009DFF", "#FF004C", "#FFFFFF", "#FFA200"]
    
    try:
        # Create the video
        video_path = typing_to_mp4(
            text=text,
            output_file=output_file,
            bg_image=bg_image,
            fps=6,
            hold_end=30,
            text_color=color[random.randrange(len(color))],
            verbose=verbose
        )
        
        # Add any test files to cleanup list if they exist
        temp_files.extend(["test_banner_frame.png", "test_frame_start.png", "test_frame_middle.png", "test_frame_end.png"])
        
        if cleanup:
            cleanup_temp_files(*temp_files)
        
        return video_path
        
    except Exception as e:
        if cleanup:
            cleanup_temp_files(*temp_files)
        raise e

if __name__ == "__main__":
    # Use your background image - update this path!
    bg_path = "bg.png"  # Make sure this matches your actual image filename
    
    print(f"Looking for background image at: {os.path.abspath(bg_path)}")
    
    if not os.path.exists(bg_path):
        print(f"ERROR: Background image '{bg_path}' not found!")
        print("Please make sure your image file is in the same directory as this script")
        print("Current directory contents:")
        for file in os.listdir('.'):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                print(f"  Found image: {file}")
    
    # Create the full video
    print("Creating terminal-banner typing video...")
    try:
        output_video = typing_to_mp4(
            "Welcome Toshith29!",
            "coco.mp4",
            bg_image=bg_path,
            fps=5,  # Slightly slower for better readability
            verbose=True  # Enable logging for manual testing
        )
        print(f"Success! Video created: {output_video}")
        
    except Exception as e:
        print(f"Failed to create video: {e}")
        print("Make sure you have: pip install cairosvg pillow imageio imageio-ffmpeg numpy")

    # Example for bot usage (silent):
    print("\n--- Bot Usage Example ---")
    try:
        bot_video = create_welcome_video(
            username="Toshith29",
            output_file="bot_welcome.mp4", 
            bg_image=bg_path,
            cleanup=True,  # Clean up temp files
            verbose=False  # Silent operation
        )
        print(f"Bot video created silently: {bot_video}")
    except Exception as e:
        print(f"Bot video creation failed: {e}")