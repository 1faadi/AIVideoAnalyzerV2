import cv2
import base64
import json
import sys
import os
import tempfile
import numpy as np
from pathlib import Path

# Try to import scikit-image, fallback to basic similarity if not available
try:
    from skimage.metrics import structural_similarity as ssim
    HAS_SCIKIT_IMAGE = True
except ImportError:
    print("Warning: scikit-image not available, using basic similarity detection", file=sys.stderr)
    HAS_SCIKIT_IMAGE = False

def detect_motion(frame1, frame2, threshold=1000):
    """
    Detect significant motion between two frames
    Returns motion score (higher = more motion)
    """
    try:
        if frame1 is None or frame2 is None:
            return 0
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY) if len(frame1.shape) == 3 else frame1
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY) if len(frame2.shape) == 3 else frame2
        
        # Resize for faster processing
        gray1 = cv2.resize(gray1, (320, 240))
        gray2 = cv2.resize(gray2, (320, 240))
        
        # Apply Gaussian blur to reduce noise
        gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
        gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
        
        # Calculate absolute difference
        frame_diff = cv2.absdiff(gray1, gray2)
        
        # Threshold the difference
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Calculate total motion area
        motion_area = sum(cv2.contourArea(contour) for contour in contours if cv2.contourArea(contour) > 50)
        
        return motion_area
        
    except Exception as e:
        print(f"Motion detection error: {e}", file=sys.stderr)
        return 0

def is_frame_quality_acceptable(frame, brightness_threshold=30, blur_threshold=50):
    """
    Check if frame quality is acceptable for analysis
    """
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        
        # Check brightness (avoid very dark frames)
        mean_brightness = np.mean(gray)
        if mean_brightness < brightness_threshold:
            return False
        
        # Check blur (using Laplacian variance)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < blur_threshold:
            return False
        
        return True
        
    except Exception as e:
        print(f"Quality check error: {e}", file=sys.stderr)
        return True  # Default to accepting frame if check fails

def calculate_frame_similarity(frame1, frame2, threshold=0.85):
    """
    Enhanced similarity calculation with motion awareness
    Returns True if frames are similar (above threshold)
    """
    try:
        if frame1 is None or frame2 is None:
            return False
        
        # Convert to grayscale for comparison
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY) if len(frame1.shape) == 3 else frame1
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY) if len(frame2.shape) == 3 else frame2
        
        # Resize to standard size for faster comparison
        target_size = (160, 120)
        gray1_resized = cv2.resize(gray1, target_size)
        gray2_resized = cv2.resize(gray2, target_size)
        
        similarity_scores = []
        
        if HAS_SCIKIT_IMAGE:
            # Use SSIM for structural similarity
            ssim_score = ssim(gray1_resized, gray2_resized)
            similarity_scores.append(ssim_score)
        
        # Use histogram comparison
        hist1 = cv2.calcHist([gray1_resized], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2_resized], [0], None, [256], [0, 256])
        hist_score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        similarity_scores.append(hist_score)
        
        # Use template matching
        try:
            result = cv2.matchTemplate(gray1_resized, gray2_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            similarity_scores.append(max_val)
        except:
            pass
        
        # Use the maximum similarity score
        if similarity_scores:
            max_similarity = max(similarity_scores)
            return max_similarity > threshold
        
        return False
        
    except Exception as e:
        print(f"Error calculating frame similarity: {e}", file=sys.stderr)
        return False

def extract_frames_with_opencv(video_path, output_dir, frame_interval=1, similarity_threshold=0.70):
    """
    Extract frames from video using OpenCV with real-time similarity checking
    """
    try:
        # Open video with OpenCV
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # Video info logged to stderr to avoid JSON parsing issues
        print(f"Video info: {fps} FPS, {total_frames} total frames, {duration:.2f}s duration", file=sys.stderr)
        print(f"Similarity threshold: {similarity_threshold}", file=sys.stderr)
        
        extracted_frames = []
        frame_count = 0
        last_saved_frame = None
        skipped_frames = 0
        
        # Extract frames every frame_interval seconds with similarity checking
        current_time = 0
        while current_time < duration:
            # Calculate frame number for this time
            frame_number = int(current_time * fps)
            
            # Set video position to specific frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                print(f"Could not read frame at {current_time:.1f}s", file=sys.stderr)
                current_time += frame_interval
                continue
            
            # Resize frame to standard size
            frame = cv2.resize(frame, (640, 480))
            
            # Relaxed quality check - only skip extremely poor frames
            if not is_frame_quality_acceptable(frame, brightness_threshold=15, blur_threshold=25):
                print(f"Extremely poor quality frame at {current_time:.1f}s - skipping", file=sys.stderr)
                current_time += frame_interval
                continue
            
            # Intensive analysis mode - more selective but comprehensive
            should_save = True
            if last_saved_frame is not None:
                # Check motion with lower threshold for more sensitivity
                motion_score = detect_motion(last_saved_frame, frame)
                motion_threshold = 800  # Lower threshold = more sensitive to motion
                
                if motion_score > motion_threshold:
                    # Motion detected - always save
                    should_save = True
                    print(f"Motion detected ({motion_score}), saving frame at {current_time:.1f}s", file=sys.stderr)
                else:
                    # Check similarity with stricter threshold (save more frames)
                    is_similar = calculate_frame_similarity(last_saved_frame, frame, similarity_threshold + 0.05)
                    if is_similar:
                        # Even for similar frames, save every 3rd one for comprehensive coverage
                        if skipped_frames % 3 == 2:  # Save every 3rd similar frame
                            should_save = True
                            print(f"Periodic save of similar frame at {current_time:.1f}s for comprehensive analysis", file=sys.stderr)
                        else:
                            should_save = False
                            skipped_frames += 1
                            print(f"Frame at {current_time:.1f}s is similar - skipping {skipped_frames}/3", file=sys.stderr)
                    else:
                        # Different frame - definitely save
                        should_save = True
            
            if should_save:
                # Create filename
                minutes = int(current_time // 60)
                seconds = int(current_time % 60)
                timestamp = f"{minutes:02d}m{seconds:02d}s"
                filename = f"frame_{frame_count}_{timestamp}.jpg"
                filepath = os.path.join(output_dir, filename)
                
                # Save frame as image
                success = cv2.imwrite(filepath, frame)
                if success:
                    # Convert to base64 for compatibility
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    extracted_frames.append({
                        "time": f"{minutes:02d}:{seconds:02d}",
                        "frame_number": frame_count,
                        "filename": filename,
                        "filepath": filepath,
                        "image_base64": frame_base64,
                        "imageUrl": f"/temp/{filename}"
                    })
                    
                    # Update last saved frame for next comparison
                    last_saved_frame = frame.copy()
                    
                    print(f"Extracted unique frame {frame_count + 1}: {filename} at {minutes:02d}:{seconds:02d}", file=sys.stderr)
                    frame_count += 1
                else:
                    print(f"Failed to save frame at {current_time:.1f}s", file=sys.stderr)
            
            # Move to next interval
            current_time += frame_interval
        
        # Clean up
        cap.release()
        
        print(f"Extraction complete: {frame_count} unique frames saved, {skipped_frames} similar frames skipped", file=sys.stderr)
        
        return {
            "success": True,
            "frames": extracted_frames,
            "total_frames_extracted": frame_count,
            "frames_skipped": skipped_frames,
            "similarity_threshold": similarity_threshold,
            "video_info": {
                "duration": duration,
                "fps": fps,
                "total_frames": total_frames,
                "frame_interval": frame_interval,
                "method": "opencv_with_similarity"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "frames": []
        }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "Usage: python extract_frames_opencv.py <video_file_path> <output_directory> [similarity_threshold]"}))
        sys.exit(1)
    
    video_path = sys.argv[1]
    output_dir = sys.argv[2]
    similarity_threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.70
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    result = extract_frames_with_opencv(video_path, output_dir, similarity_threshold=similarity_threshold)
    print(json.dumps(result))
