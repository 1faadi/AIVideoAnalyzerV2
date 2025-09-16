import os
import json
import sys
import base64
import requests
import cv2
import numpy as np
from pathlib import Path
import shutil
import argparse
from datetime import datetime

# Redirect all output to stderr except for final JSON result
original_stdout = sys.stdout

# Try to import scikit-image, fallback to basic similarity if not available
try:
    from skimage.metrics import structural_similarity as ssim
    HAS_SCIKIT_IMAGE = True
except ImportError:
    print("Warning: scikit-image not available, using basic similarity detection", file=sys.stderr)
    HAS_SCIKIT_IMAGE = False

# Try to import vision detector for object detection
try:
    import logging
    # Suppress YOLO startup messages to prevent JSON parsing issues
    os.environ['YOLO_VERBOSE'] = 'False'
    logging.getLogger('ultralytics').setLevel(logging.ERROR)
    
    # Temporarily redirect stdout to stderr during YOLO import
    sys.stdout = sys.stderr
    from ultralytics import YOLO as VisionDetector
    sys.stdout = original_stdout
    
    HAS_YOLO = True
    print("Vision detector is available for object detection", file=sys.stderr)
except ImportError:
    sys.stdout = original_stdout
    print("Warning: ultralytics not available, object detection disabled", file=sys.stderr)
    HAS_YOLO = False
except Exception as e:
    sys.stdout = original_stdout
    print(f"Warning: vision detector import failed with error: {e}, object detection disabled", file=sys.stderr)
    HAS_YOLO = False

def detect_objects_with_yolo(image_path, confidence_threshold=0.10):
    """
    Enhanced YOLO detection with comprehensive object detection
    Uses multiple models and lower thresholds to catch all objects
    """
    if not HAS_YOLO:
        return []
    
    try:
        detected_objects = []
        
        # Try multiple detector models for enhanced detection
        model_configs = [
            {"model": "yolo11n.pt", "name": "nano", "conf": confidence_threshold},
            {"model": "yolo11s.pt", "name": "small", "conf": confidence_threshold * 0.8},  # Even lower threshold
            {"model": "yolo11m.pt", "name": "medium", "conf": confidence_threshold * 0.7}   # Lowest threshold
        ]
        
        all_detections = []
        
        for config in model_configs:
            try:
                print(f"Running detector {config['name']} with confidence {config['conf']:.2f}...", file=sys.stderr)
                # Suppress YOLO verbose output during model loading
                import logging
                logging.getLogger('ultralytics').setLevel(logging.ERROR)
                
                # Temporarily redirect stdout to stderr during model loading
                sys.stdout = sys.stderr
                model = VisionDetector(config["model"])
                sys.stdout = original_stdout
                
                # Run inference with lower confidence and higher IoU threshold for comprehensive detection
                # Temporarily redirect stdout to stderr during inference
                sys.stdout = sys.stderr
                results = model(
                    image_path, 
                    conf=config["conf"],      # Low confidence to catch more objects
                    iou=0.7,                  # High IoU to reduce duplicate detections
                    agnostic_nms=True,        # Class-agnostic NMS
                    max_det=100,              # Allow more detections
                    verbose=False
                )
                sys.stdout = original_stdout
                
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            # Get bounding box coordinates (xyxy format)
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            
                            # Get confidence and class
                            confidence = float(box.conf[0])
                            class_id = int(box.cls[0])
                            class_name = model.names[class_id]
                            
                            # Convert to normalized coordinates (0-1)
                            img = cv2.imread(image_path)
                            if img is not None:
                                height, width = img.shape[:2]
                                
                                # Convert to normalized x, y, w, h format
                                x_norm = x1 / width
                                y_norm = y1 / height
                                w_norm = (x2 - x1) / width
                                h_norm = (y2 - y1) / height
                                
                                # Classify object type for safety assessment
                                safety_category = classify_object_for_safety(class_name)
                                
                                bbox_position = {
                                    "x": x_norm,
                                    "y": y_norm,
                                    "w": w_norm,
                                    "h": h_norm
                                }
                                
                                # Apply enhanced filtering
                                if not is_realistic_detection(class_name, bbox_position, confidence):
                                    continue  # Skip unrealistic detections
                                
                                detection = {
                                    "class_name": class_name,
                                    "confidence": confidence,
                                    "bbox": bbox_position,
                                    "safety_category": safety_category,
                                    "potential_hazard": is_critical_safety_hazard(class_name, confidence, bbox_position),
                                    "model_used": config["name"],
                                    "detection_id": f"{class_name}_{x_norm:.3f}_{y_norm:.3f}"
                                }
                                all_detections.append(detection)
                
                print(f"Detector {config['name']} detected {len([d for d in all_detections if d['model_used'] == config['name']])} objects", file=sys.stderr)
                
            except Exception as model_error:
                print(f"Could not load detector {config['name']}: {model_error}, trying next...", file=sys.stderr)
                continue
        
        # Remove duplicate detections using distance-based filtering
        unique_detections = remove_duplicate_detections(all_detections)
        
        print(f"Total detections after deduplication: {len(unique_detections)}", file=sys.stderr)
        return unique_detections
        
    except Exception as e:
        print(f"Error in enhanced YOLO detection: {e}", file=sys.stderr)
        return []

def remove_duplicate_detections(detections, distance_threshold=0.1):
    """
    Remove duplicate detections based on spatial proximity and class similarity
    """
    if not detections:
        return []
    
    unique_detections = []
    
    for detection in detections:
        is_duplicate = False
        
        for existing in unique_detections:
            # Check if same class and close proximity
            if (detection['class_name'] == existing['class_name']):
                # Calculate center distance
                center1 = (detection['bbox']['x'] + detection['bbox']['w']/2, 
                          detection['bbox']['y'] + detection['bbox']['h']/2)
                center2 = (existing['bbox']['x'] + existing['bbox']['w']/2,
                          existing['bbox']['y'] + existing['bbox']['h']/2)
                
                distance = ((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)**0.5
                
                if distance < distance_threshold:
                    # Keep the one with higher confidence
                    if detection['confidence'] > existing['confidence']:
                        unique_detections.remove(existing)
                        unique_detections.append(detection)
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            unique_detections.append(detection)
    
    return unique_detections

def classify_object_for_safety(class_name):
    """
    Classify detected objects into safety-relevant categories
    """
    safety_categories = {
        "vehicle": ["car", "truck", "bus", "motorcycle", "bicycle"],
        "person": ["person"],
        "equipment": ["chair", "desk", "table", "laptop", "monitor", "keyboard"],
        "container": ["bottle", "cup", "bowl", "box", "suitcase", "handbag", "backpack"],
        "obstacles": ["bench", "potted plant", "vase", "sports ball"],
        "waste": ["trash", "recycling", "garbage"],
        "warning": ["stop sign", "traffic light", "fire hydrant"],
        "structure": ["door", "window", "wall"]
    }
    
    class_lower = class_name.lower()
    for category, items in safety_categories.items():
        if any(item in class_lower for item in items):
            return category
    
    return "other"

def get_adaptive_confidence_threshold(class_name, scene_context="warehouse"):
    """
    Get adaptive confidence threshold based on object type and context
    Higher thresholds for less critical objects, lower for safety-critical ones
    """
    class_lower = class_name.lower()
    
    # Critical safety objects - lower threshold (catch more)
    if any(item in class_lower for item in ["car", "truck", "forklift", "vehicle", "bicycle"]):
        return 0.20  # Even more sensitive for vehicles
    
    # Blocking furniture/equipment - lower threshold for intensive analysis
    if any(item in class_lower for item in ["table", "desk", "cabinet", "ladder", "cart", "box", "container"]):
        return 0.25  # More inclusive
    
    # Smaller objects - reduced threshold for comprehensive detection
    if any(item in class_lower for item in ["person", "chair", "bag", "bottle", "phone"]):
        return 0.35  # More inclusive
    
    # Default threshold - more inclusive
    return 0.30

def is_critical_safety_hazard(class_name, confidence, bbox_position, base_threshold=0.20):
    """
    Enhanced smart filtering with adaptive confidence thresholds
    """
    # Get adaptive threshold for this object type
    adaptive_threshold = get_adaptive_confidence_threshold(class_name)
    effective_threshold = max(base_threshold, adaptive_threshold)
    
    if confidence < effective_threshold:
        return False
    
    class_lower = class_name.lower()
    
    # Only critical hazards that definitely block pathways
    critical_hazards = {
        # Vehicles - always critical in hallways
        "vehicles": ["car", "truck", "bus", "motorcycle", "bicycle", "motorbike"],
        
        # Large furniture blocking pathways
        "blocking_furniture": ["table", "desk", "cabinet", "shelf", "couch", "wardrobe"],
        
        # Large containers/boxes
        "large_containers": ["box", "container", "barrel", "bin", "crate", "pallet"],
        
        # Equipment that shouldn't be in hallways
        "equipment": ["ladder", "cart", "trolley", "machine", "forklift"]
    }
    
    # Check if object is in a critical category
    for category, items in critical_hazards.items():
        if any(item in class_lower for item in items):
            # Additional check: object should be in pathway area (center region)
            center_x = bbox_position.get('x', 0) + bbox_position.get('w', 0) / 2
            center_y = bbox_position.get('y', 0) + bbox_position.get('h', 0) / 2
            
            # Focus on center pathway areas (avoid wall/edge detections)
            if 0.2 <= center_x <= 0.8 and 0.3 <= center_y <= 0.9:
                return True
    
    return False

def is_realistic_detection(class_name, bbox_position, confidence):
    """
    Filter out unrealistic detections based on size and position
    """
    w = bbox_position.get('w', 0)
    h = bbox_position.get('h', 0)
    area = w * h
    
    class_lower = class_name.lower()
    
    # Size constraints (as percentage of image)
    if area < 0.001:  # Too small (less than 0.1% of image)
        return False
    
    if area > 0.5:    # Too large (more than 50% of image)
        return False
    
    # Object-specific size validation
    if any(vehicle in class_lower for vehicle in ["car", "truck", "bus"]):
        # Vehicles should be reasonably sized
        if area < 0.01 or area > 0.4:  # 1% to 40% of image
            return False
    
    if "person" in class_lower:
        # People should be reasonable size
        if area < 0.005 or area > 0.2:  # 0.5% to 20% of image
            return False
    
    # Position validation - avoid extreme edges for main objects
    center_x = bbox_position.get('x', 0) + w / 2
    center_y = bbox_position.get('y', 0) + h / 2
    
    # Skip objects at very edges (likely partial/cut-off)
    if center_x < 0.05 or center_x > 0.95 or center_y < 0.05 or center_y > 0.95:
        if confidence < 0.7:  # Only keep high-confidence edge detections
            return False
    
    return True

def assess_hazard_severity(class_name, confidence, bbox_position):
    """
    Assess the severity of a confirmed hazard based on type, size, and position
    """
    class_lower = class_name.lower()
    
    # Calculate object size
    object_size = bbox_position.get('w', 0) * bbox_position.get('h', 0)
    
    # Vehicles are always critical
    if any(v in class_lower for v in ["car", "truck", "bus", "motorcycle", "bicycle"]):
        return {
            "severity": "critical",
            "reason": "Vehicle blocking emergency access",
            "priority": 1,
            "immediate_action": True
        }
    
    # Large objects in pathway
    if object_size > 0.1:  # Large object (>10% of frame)
        return {
            "severity": "high",
            "reason": "Large object blocking significant pathway area",
            "priority": 2,
            "immediate_action": True
        }
    
    # Medium objects in center pathway
    center_x = bbox_position.get('x', 0) + bbox_position.get('w', 0) / 2
    if 0.3 <= center_x <= 0.7 and object_size > 0.05:
        return {
            "severity": "medium",
            "reason": "Object in main pathway area",
            "priority": 3,
            "immediate_action": False
        }
    
    # Default for confirmed hazards
    return {
        "severity": "low",
        "reason": "Minor pathway obstruction",
        "priority": 4,
        "immediate_action": False
    }

def generate_mitigation_strategies(detected_objects, ai_analysis):
    """
    Generate comprehensive mitigation strategies based on YOLO detections and AI analysis
    """
    mitigations = []
    
    # Categorize detected objects for detailed analysis
    object_categories = {
        "vehicles": [],
        "furniture": [],
        "personal_items": [],
        "containers": [],
        "trip_hazards": [],
        "equipment": [],
        "people": [],
        "other_hazards": []
    }
    
    # Categorize all detected objects
    for obj in detected_objects:
        if obj.get("potential_hazard", False):
            category = obj.get("safety_category", "other")
            class_name = obj.get("class_name", "unknown")
            
            if category == "vehicle" or any(v in class_name.lower() for v in ["car", "truck", "bus", "motorcycle", "bicycle"]):
                object_categories["vehicles"].append(obj)
            elif category == "person" or "person" in class_name.lower():
                object_categories["people"].append(obj)
            elif any(f in class_name.lower() for f in ["chair", "table", "bench", "desk", "cabinet"]):
                object_categories["furniture"].append(obj)
            elif any(p in class_name.lower() for p in ["bag", "suitcase", "backpack", "luggage"]):
                object_categories["personal_items"].append(obj)
            elif any(c in class_name.lower() for c in ["box", "container", "barrel", "bucket"]):
                object_categories["containers"].append(obj)
            elif any(t in class_name.lower() for t in ["bottle", "cup", "ball", "book", "phone"]):
                object_categories["trip_hazards"].append(obj)
            elif any(e in class_name.lower() for e in ["monitor", "computer", "printer", "machine"]):
                object_categories["equipment"].append(obj)
            else:
                object_categories["other_hazards"].append(obj)
    
    # Generate specific mitigation strategies for each category
    
    # VEHICLES - Critical Priority
    if object_categories["vehicles"]:
        vehicle_details = [f"{obj['class_name']} (conf: {obj['confidence']:.2f})" for obj in object_categories["vehicles"]]
        mitigations.append({
            "type": "vehicle_parking_violation",
            "severity": "critical",
            "urgency": "immediate",
            "description": f"Detected {len(object_categories['vehicles'])} vehicle(s): {', '.join(vehicle_details)}",
            "specific_risks": [
                "Blocks emergency vehicle access",
                "Prevents fire brigade movement",
                "Obstructs evacuation routes",
                "Creates fire safety violations"
            ],
            "mitigation_steps": [
                "IMMEDIATE: Contact vehicle owners for immediate removal",
                "IMMEDIATE: Deploy traffic cones to mark violation area",
                "SHORT-TERM: Install permanent 'No Parking' signage",
                "SHORT-TERM: Paint red lines on pavement",
                "LONG-TERM: Install physical barriers (bollards)",
                "LONG-TERM: Implement automated monitoring system"
            ],
            "timeline": "Immediate action required within 30 minutes",
            "responsible_party": "Security/Facilities Management",
            "estimated_cost": "Low ($100-500 for signage) to Medium ($2000-5000 for barriers)",
            "emergency_impact": "Critical - directly blocks emergency vehicle access",
            "compliance": "Fire safety code violation - immediate remediation required"
        })
    
    # FURNITURE - High Priority
    if object_categories["furniture"]:
        furniture_details = [f"{obj['class_name']} (conf: {obj['confidence']:.2f})" for obj in object_categories["furniture"]]
        mitigations.append({
            "type": "furniture_obstruction",
            "severity": "high",
            "urgency": "short-term",
            "description": f"Detected {len(object_categories['furniture'])} furniture item(s): {', '.join(furniture_details)}",
            "specific_risks": [
                "Reduces pathway width below minimum requirements",
                "Impedes emergency evacuation flow",
                "Creates bottlenecks during emergencies"
            ],
            "mitigation_steps": [
                "IMMEDIATE: Relocate furniture to designated areas",
                "SHORT-TERM: Mark minimum pathway widths with tape",
                "MEDIUM-TERM: Designate specific furniture zones",
                "LONG-TERM: Implement 5S workplace organization"
            ],
            "timeline": "Complete within 24 hours",
            "responsible_party": "Warehouse Operations/Maintenance",
            "estimated_cost": "Low ($50-200 for marking materials)",
            "emergency_impact": "High - significantly impedes evacuation flow"
        })
    
    # CONTAINERS AND BOXES - Medium Priority
    if object_categories["containers"]:
        container_details = [f"{obj['class_name']} (conf: {obj['confidence']:.2f})" for obj in object_categories["containers"]]
        mitigations.append({
            "type": "container_storage_violation",
            "severity": "medium",
            "urgency": "short-term",
            "description": f"Detected {len(object_categories['containers'])} container(s): {', '.join(container_details)}",
            "specific_risks": [
                "Creates pathway obstacles",
                "Potential for contents to spill",
                "May fall and cause injuries"
            ],
            "mitigation_steps": [
                "IMMEDIATE: Move containers to designated storage areas",
                "SHORT-TERM: Secure containers properly",
                "MEDIUM-TERM: Install proper shelving systems",
                "LONG-TERM: Implement container management protocols"
            ],
            "timeline": "Complete within 2-3 days",
            "responsible_party": "Warehouse Staff/Supervisors",
            "estimated_cost": "Medium ($500-2000 for storage solutions)",
            "emergency_impact": "Medium - creates obstacles but pathways remain navigable"
        })
    
    # TRIP HAZARDS - Medium Priority
    if object_categories["trip_hazards"]:
        trip_details = [f"{obj['class_name']} (conf: {obj['confidence']:.2f})" for obj in object_categories["trip_hazards"]]
        mitigations.append({
            "type": "trip_hazard_elimination",
            "severity": "medium",
            "urgency": "immediate",
            "description": f"Detected {len(object_categories['trip_hazards'])} trip hazard(s): {', '.join(trip_details)}",
            "specific_risks": [
                "Causes falls and injuries",
                "Slows emergency evacuation",
                "Creates liability issues"
            ],
            "mitigation_steps": [
                "IMMEDIATE: Remove or secure loose objects",
                "IMMEDIATE: Clean up spills and debris",
                "SHORT-TERM: Install adequate trash receptacles",
                "MEDIUM-TERM: Implement regular cleaning schedule",
                "LONG-TERM: Staff training on housekeeping protocols"
            ],
            "timeline": "Immediate removal within 1 hour",
            "responsible_party": "Cleaning/Maintenance Staff",
            "estimated_cost": "Low ($20-100 for cleaning supplies)",
            "emergency_impact": "Medium - may cause delays during evacuation"
        })
    
    # PERSONAL ITEMS - Low Priority but Important
    if object_categories["personal_items"]:
        personal_details = [f"{obj['class_name']} (conf: {obj['confidence']:.2f})" for obj in object_categories["personal_items"]]
        mitigations.append({
            "type": "personal_belongings_management",
            "severity": "low",
            "urgency": "short-term",
            "description": f"Detected {len(object_categories['personal_items'])} personal item(s): {', '.join(personal_details)}",
            "specific_risks": [
                "Creates pathway clutter",
                "May contain valuable items (security risk)",
                "Indicates lack of proper storage protocols"
            ],
            "mitigation_steps": [
                "IMMEDIATE: Relocate to designated personal storage areas",
                "SHORT-TERM: Install personal lockers if needed",
                "MEDIUM-TERM: Implement clear desk/area policies",
                "LONG-TERM: Staff training on personal item management"
            ],
            "timeline": "Complete within 1 week",
            "responsible_party": "HR/Facilities Management",
            "estimated_cost": "Medium ($200-1000 for storage solutions)",
            "emergency_impact": "Low - minimal impact on emergency procedures"
        })
    
    # PEOPLE - Training and Awareness
    if object_categories["people"]:
        mitigations.append({
            "type": "personnel_safety_training",
            "severity": "medium",
            "urgency": "short-term",
            "description": f"Detected {len(object_categories['people'])} person(s) in area",
            "specific_risks": [
                "Personnel may not be aware of emergency procedures",
                "Potential for panic during emergencies",
                "May inadvertently block evacuation routes"
            ],
            "mitigation_steps": [
                "IMMEDIATE: Conduct emergency procedure briefing",
                "SHORT-TERM: Post emergency evacuation maps",
                "MEDIUM-TERM: Conduct emergency evacuation drills",
                "LONG-TERM: Implement regular safety training program"
            ],
            "timeline": "Initial briefing within 24 hours, full training within 1 month",
            "responsible_party": "Safety Officer/HR Department",
            "estimated_cost": "Low ($100-500 for training materials)",
            "emergency_impact": "Variable - depends on personnel emergency preparedness"
        })
    
    # Add AI-specific mitigations with enhanced detail
    if ai_analysis.get("incorrectParking"):
        mitigations.append({
            "type": "ai_detected_parking_violation",
            "severity": "critical",
            "urgency": "immediate",
            "description": "AI visual analysis detected parking violations affecting emergency access",
            "specific_risks": [
                "Confirmed visual obstruction of emergency routes",
                "Fire code compliance violation",
                "Insurance liability issues"
            ],
            "mitigation_steps": [
                "IMMEDIATE: Document violation with photos",
                "IMMEDIATE: Contact vehicle owners",
                "SHORT-TERM: Install physical barriers",
                "LONG-TERM: Implement automated monitoring"
            ],
            "timeline": "Immediate action required",
            "responsible_party": "Security/Management",
            "estimated_cost": "Medium ($1000-3000 for comprehensive solution)",
            "emergency_impact": "Critical - confirmed emergency access obstruction"
        })
    
    if ai_analysis.get("wasteMaterial"):
        mitigations.append({
            "type": "ai_detected_waste_debris",
            "severity": "medium",
            "urgency": "immediate",
            "description": "AI visual analysis detected waste or debris in pathways",
            "specific_risks": [
                "Confirmed pathway obstruction",
                "Slip and trip hazards",
                "Fire fuel load concerns"
            ],
            "mitigation_steps": [
                "IMMEDIATE: Remove waste and debris",
                "SHORT-TERM: Increase cleaning frequency",
                "MEDIUM-TERM: Install additional waste receptacles",
                "LONG-TERM: Implement waste management protocols"
            ],
            "timeline": "Complete cleaning within 2 hours",
            "responsible_party": "Cleaning/Maintenance Staff",
            "estimated_cost": "Low ($50-200 for enhanced cleaning)",
            "emergency_impact": "Medium - creates evacuation hazards"
        })
    
    # Add overall assessment if no specific hazards found
    if not any(object_categories.values()) and not ai_analysis.get("incorrectParking") and not ai_analysis.get("wasteMaterial"):
        mitigations.append({
            "type": "preventive_maintenance",
            "severity": "low",
            "urgency": "long-term",
            "description": "No immediate hazards detected - implement preventive measures",
            "specific_risks": [
                "Future hazard development",
                "Gradual safety standard degradation"
            ],
            "mitigation_steps": [
                "ONGOING: Maintain regular safety inspections",
                "MONTHLY: Review and update safety protocols",
                "QUARTERLY: Conduct comprehensive safety audits",
                "ANNUALLY: Update emergency response procedures"
            ],
            "timeline": "Ongoing preventive program",
            "responsible_party": "Safety Committee",
            "estimated_cost": "Low ($100-300 monthly for ongoing programs)",
            "emergency_impact": "Preventive - maintains safety standards"
        })
    
    return mitigations

def calculate_basic_similarity(img1, img2):
    """
    Basic similarity calculation using histogram comparison
    """
    try:
        # Calculate histograms
        hist1 = cv2.calcHist([img1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2], [0], None, [256], [0, 256])
        
        # Compare histograms using correlation
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return correlation
        
    except Exception:
        return 0.0

def calculate_image_similarity(img1_path, img2_path, threshold=0.80):
    """
    Calculate similarity between two images using multiple methods for better detection
    Returns True if images are similar (above threshold)
    """
    try:
        # Read images
        img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
        
        if img1 is None or img2 is None:
            return False
        
        # Resize to standard size for comparison (smaller for speed)
        target_size = (160, 120)  # Smaller size for faster comparison
        img1_resized = cv2.resize(img1, target_size)
        img2_resized = cv2.resize(img2, target_size)
        
        similarity_scores = []
        
        if HAS_SCIKIT_IMAGE:
            # Use SSIM for structural similarity
            ssim_score = ssim(img1_resized, img2_resized)
            similarity_scores.append(ssim_score)
        
        # Use histogram comparison as additional check
        hist_score = calculate_basic_similarity(img1_resized, img2_resized)
        similarity_scores.append(hist_score)
        
        # Use template matching as another check
        try:
            result = cv2.matchTemplate(img1_resized, img2_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            similarity_scores.append(max_val)
        except:
            pass
        
        # Use the maximum similarity score from all methods
        if similarity_scores:
            max_similarity = max(similarity_scores)
            print(f"Similarity scores: {[f'{s:.3f}' for s in similarity_scores]}, max: {max_similarity:.3f}, threshold: {threshold:.3f}", file=sys.stderr)
            return max_similarity > threshold
        
        return False
        
    except Exception as e:
        print(f"Error calculating similarity: {e}", file=sys.stderr)
        return False

def convert_grid_cells_to_bounding_box(grid_cells_string):
    """
    Convert grid cell notation (e.g., "A1", "B2-B3", "A1-A2-B1-B2") to normalized bounding box coordinates
    Grid is 4x3: A1-A4 (top), B1-B4 (middle), C1-C4 (bottom)
    """
    try:
        if not grid_cells_string or grid_cells_string.strip() == "":
            return {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}  # Default small box
        
        # Parse grid cells
        cells = [cell.strip() for cell in grid_cells_string.replace("-", ",").split(",")]
        if not cells:
            return {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}
        
        # Grid layout: 4 columns, 3 rows
        # A1-A4: row 0, cols 0-3
        # B1-B4: row 1, cols 0-3  
        # C1-C4: row 2, cols 0-3
        grid_positions = []
        
        for cell in cells:
            cell = cell.upper().strip()
            if len(cell) >= 2:
                row_letter = cell[0]
                col_number = cell[1:]
                
                try:
                    col_index = int(col_number) - 1  # Convert 1-4 to 0-3
                    if row_letter == 'A':
                        row_index = 0
                    elif row_letter == 'B':
                        row_index = 1
                    elif row_letter == 'C':
                        row_index = 2
                    else:
                        continue
                    
                    if 0 <= col_index <= 3 and 0 <= row_index <= 2:
                        grid_positions.append((row_index, col_index))
                except ValueError:
                    continue
        
        if not grid_positions:
            return {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}
        
        # Calculate bounding box from grid positions
        min_row = min(pos[0] for pos in grid_positions)
        max_row = max(pos[0] for pos in grid_positions)
        min_col = min(pos[1] for pos in grid_positions)
        max_col = max(pos[1] for pos in grid_positions)
        
        # Convert to normalized coordinates (0-1)
        # Each cell is 1/4 width, 1/3 height
        cell_width = 1.0 / 4.0
        cell_height = 1.0 / 3.0
        
        x = min_col * cell_width
        y = min_row * cell_height
        w = (max_col - min_col + 1) * cell_width
        h = (max_row - min_row + 1) * cell_height
        
        # Ensure values are within bounds
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        w = max(0.05, min(1.0 - x, w))  # Minimum 5% width
        h = max(0.05, min(1.0 - y, h))  # Minimum 5% height
        
        return {"x": x, "y": y, "w": w, "h": h}
        
    except Exception as e:
        print(f"Error converting grid cells '{grid_cells_string}': {e}", file=sys.stderr)
        return {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}

def filter_unique_frames(frame_files, frames_dir, similarity_threshold=0.88):
    """
    Filter out similar frames, keeping only unique ones with improved aggressive filtering
    """
    if not frame_files:
        return []
    
    print(f"Starting frame filtering with threshold {similarity_threshold}", file=sys.stderr)
    
    # Try intelligent similarity detection first
    try:
        unique_frames = [frame_files[0]]  # Always keep the first frame
        print(f"Starting with frame: {frame_files[0]}", file=sys.stderr)
        
        # Balanced approach: moderate frame gap and recent frame comparison
        min_frame_gap = 1  # Minimum frames to skip between selections (reduced from 2)
        last_selected_index = 0
        
        for i, current_frame in enumerate(frame_files[1:], 1):
            # Skip frames that are too close to the last selected frame
            if i - last_selected_index < min_frame_gap:
                print(f"Frame {current_frame} too close to last selected ({i - last_selected_index} gap) - skipping", file=sys.stderr)
                continue
                
            current_path = os.path.join(frames_dir, current_frame)
            is_unique = True
            
            # Only compare with the last 3 unique frames for efficiency and better filtering
            recent_unique_frames = unique_frames[-3:] if len(unique_frames) > 3 else unique_frames
            
            for unique_frame in recent_unique_frames:
                unique_path = os.path.join(frames_dir, unique_frame)
                
                if calculate_image_similarity(current_path, unique_path, similarity_threshold):
                    print(f"Frame {current_frame} is similar to {unique_frame} (threshold {similarity_threshold}) - skipping", file=sys.stderr)
                    is_unique = False
                    break
            
            if is_unique:
                unique_frames.append(current_frame)
                last_selected_index = i
                print(f"Frame {current_frame} is unique - keeping ({len(unique_frames)} total, gap: {i - (last_selected_index - len(unique_frames) + 1)})", file=sys.stderr)
        
        print(f"Intelligent filtering: {len(frame_files)} -> {len(unique_frames)} frames", file=sys.stderr)
        
        # If we still have too many frames, apply additional time-based sampling
        if len(unique_frames) > 12:  # Increased max frames from 8 to 12
            step = len(unique_frames) // 12
            sampled_unique = unique_frames[::step][:12]
            print(f"Additional sampling: {len(unique_frames)} -> {len(sampled_unique)} frames", file=sys.stderr)
            return sampled_unique
        
        return unique_frames
        
    except Exception as e:
        print(f"Error in similarity detection, using time-based sampling: {e}", file=sys.stderr)
        # Fallback: intelligent time-based sampling
        total_frames = len(frame_files)
        if total_frames <= 5:
            return frame_files  # Keep all if few frames
        elif total_frames <= 15:
            step = 3  # Every 3rd frame
        elif total_frames <= 30:
            step = 5  # Every 5th frame  
        else:
            step = max(4, total_frames // 12)  # Max 12 frames (increased from 8)
            
        sampled_frames = frame_files[::step][:12]  # Cap at 12 frames (increased from 8)
        print(f"Time-based sampling: selected {len(sampled_frames)} frames from {total_frames} total (step: {step})", file=sys.stderr)
        return sampled_frames

def process_frames_in_batches(frames_data, api_key, batch_size=5, frames_dir=None):
    """
    Process frames in batches with YOLO detection integration
    """
    all_frame_details = []
    all_yolo_detections = []
    total_batches = (len(frames_data) + batch_size - 1) // batch_size
    
    print(f"Processing {len(frames_data)} frames in {total_batches} batches of {batch_size}", file=sys.stderr)
    
    # Run YOLO detection on all frames first if available
    if HAS_YOLO and frames_dir:
        print("Running object detection on all frames...", file=sys.stderr)
        for frame_data in frames_data:
            frame_path = os.path.join(frames_dir, frame_data['filename'])
            yolo_detections = detect_objects_with_yolo(frame_path)
            all_yolo_detections.append(yolo_detections)
            print(f"Detector found {len(yolo_detections)} objects in {frame_data['filename']}", file=sys.stderr)
    else:
        # Create empty detections if YOLO not available
        all_yolo_detections = [[] for _ in frames_data]
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(frames_data))
        batch_frames = frames_data[start_idx:end_idx]
        batch_yolo_detections = all_yolo_detections[start_idx:end_idx]
        
        print(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_frames)} frames)...", file=sys.stderr)
        
        try:
            batch_results = analyze_batch_with_openrouter(batch_frames, api_key, batch_num, start_idx, batch_yolo_detections)
            if batch_results.get("success"):
                batch_frame_details = batch_results.get("analysis", {}).get("frameDetails", [])
                all_frame_details.extend(batch_frame_details)
                print(f"Batch {batch_num + 1} completed successfully - {len(batch_frame_details)} frames analyzed", file=sys.stderr)
            else:
                print(f"Batch {batch_num + 1} failed: {batch_results.get('error', 'Unknown error')}", file=sys.stderr)
                # Continue with next batch even if one fails
                
        except Exception as e:
            print(f"Error processing batch {batch_num + 1}: {e}", file=sys.stderr)
            continue
    
    return all_frame_details, all_yolo_detections

def analyze_batch_with_openrouter(batch_frames, api_key, batch_num, start_frame_idx, yolo_detections=None):
    """
    Analyze a single batch of frames with OpenRouter, enhanced with YOLO detection data
    """
    try:
        # Prepare detector context if available
        yolo_context = ""
        if yolo_detections and len(yolo_detections) > 0:
            yolo_summary = []
            for frame_idx, detections in enumerate(yolo_detections):
                if detections:
                    detection_summary = f"Frame {start_frame_idx + frame_idx}: Detected {len(detections)} objects - "
                    detection_summary += ", ".join([f"{d['class_name']} ({d['confidence']:.2f})" for d in detections])
                    yolo_summary.append(detection_summary)
            
            if yolo_summary:
                yolo_context = f"\n\nOBJECT DETECTION RESULTS:\n{chr(10).join(yolo_summary)}\n\nPlease cross-reference these detections with your visual analysis and provide comprehensive assessment."

        messages = [
            {
                "role": "system",
                "content": f"""You are an expert warehouse safety inspector with 20+ years of experience. Analyze these images with the precision of a certified safety auditor.

BATCH INFO: {batch_num + 1}, Frame indices start from {start_frame_idx}

🎯 ENHANCED GRID ANALYSIS SYSTEM:
Each image is divided into a precise 4x3 grid (4 columns, 3 rows) = 12 cells:
Row 1 (Top):    A1  A2  A3  A4
Row 2 (Middle): B1  B2  B3  B4  
Row 3 (Bottom): C1  C2  C3  C4

📋 SYSTEMATIC ANALYSIS PROCESS:
1. SCAN GRID METHODICALLY: Start A1→A4, then B1→B4, then C1→C4
2. IDENTIFY SAFETY HAZARDS with CONFIDENCE RATING (1-10):
   - Emergency pathway obstructions (vehicles, equipment, materials)
   - Fire safety violations (blocked exits, improper storage)
   - Forklift/vehicle unsafe positioning
   - Waste/debris creating trip hazards
   - Inadequate clearance for emergency vehicles

3. LOCATION PRECISION: Always specify exact grid cells for bounding boxes:
   - Small objects: Single cell (e.g., "A1")
   - Medium objects: Adjacent cells (e.g., "A1-A2" or "A1,B1")
   - Large objects: Multiple cells (e.g., "A1-A3" or "A1-B2")
   - Any other hazards affecting emergency response
   
2. OBJECT IDENTIFICATION: Identify all visible objects and assess their safety implications
3. PATHWAY ASSESSMENT: Evaluate emergency vehicle accessibility and evacuation route clarity
4. MITIGATION STRATEGIES: Provide specific, actionable mitigation strategies for each identified issue

For EVERY safety issue you identify, specify which GRID CELL(S) it occupies (e.g., "A1", "B2-B3", "C1-C2-C3").

Respond ONLY in strict JSON format:
{{
  "incorrectParking": boolean,
  "wasteMaterial": boolean,
  "overallExplanation": "comprehensive batch summary of findings and overall safety assessment",
  "frameDetails": [
    {{
      "frameIndex": number,
      "timestamp": "MM:SS", 
      "detailedObservations": "VERY detailed description of everything visible in this specific frame",
      "identifiedObjects": [
        {{
          "objectType": "type of object detected",
          "location": "grid cell location",
          "safetyRelevance": "how this object relates to safety",
          "confidence": "high/medium/low confidence in identification"
        }}
      ],
      "safetyIssues": [
        {{
          "type": "parking" | "waste" | "obstruction" | "hazard" | "pathway_blocked" | "equipment" | "vehicle" | "debris" | "other",
          "severity": "low" | "medium" | "high" | "critical",
          "confidence": 1-10 (numerical confidence score),
          "reasoning": "step-by-step analysis of why this is a safety issue",
          "description": "detailed description of the specific safety issue",
          "location": "specific location description (left side, center, right side, etc.)",
          "impact": "how this could affect emergency response",
          "gridCells": "grid cell(s) where this issue is located (e.g., 'A1', 'B2-B3', 'C1-C2')",
          "mitigationStrategy": "specific actionable steps to address this issue",
          "urgency": "immediate" | "short-term" | "long-term",
          "estimatedCost": "low" | "medium" | "high",
          "responsibleParty": "suggested responsible party for remediation"
        }}
      ],
      "pathwayClearance": "detailed description of pathway conditions and clearance measurements if possible",
      "emergencyAccess": "comprehensive assessment of emergency vehicle access through this area",
      "recommendedActions": [
        {{
          "action": "specific action to take",
          "priority": "high" | "medium" | "low",
          "timeframe": "immediate" | "24-hours" | "1-week" | "1-month"
        }}
      ]
    }}
  ]
}}

🚨 CRITICAL INSTRUCTIONS - FOLLOW EXACTLY:
1. ANALYZE EVERY FRAME: Create frameDetails entry for each frame (array length = image count)
2. FRAME INDEXING: Use correct frameIndex starting from {start_frame_idx}
3. CONFIDENCE SCORING: Rate every safety issue 1-10 (10 = absolutely certain)
4. GRID PRECISION: Always specify gridCells for bounding box placement
   • Grid: A1-A4 (top), B1-B4 (middle), C1-C4 (bottom)
   • Examples: "A1" (small), "A1-A2" (medium), "A1-B2" (large)
5. CHAIN-OF-THOUGHT: Include "reasoning" field explaining your analysis
6. MITIGATION FOCUS: Provide specific, actionable mitigation strategies
7. CROSS-REFERENCE: Use YOLO detection data when available for validation
8. NO ASSUMPTIONS: Only report what you can clearly see and verify
9. EMERGENCY ACCESS: Prioritize issues affecting emergency vehicle access
10. JSON ONLY: Return valid JSON with all required fields{yolo_context}"""
            },
            {
                "role": "user",
                "content": [
                    { 
                        "type": "text", 
                        "text": f"Analyze these {len(batch_frames)} warehouse hallway frames. Provide comprehensive safety analysis with detailed mitigation strategies for each frame with frameIndex starting from {start_frame_idx}." 
                    }
                ] + [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{frame['image_base64']}"}
                    } for frame in batch_frames
                ]
            }
        ]
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "Warehouse Safety Inspector"
            },
            json={
                "model": "openai/vision-model",
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            },
            timeout=120
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"OpenRouter API error: {response.status_code} - {response.text}"
            }
        
        result = response.json()
        ai_analysis = json.loads(result["choices"][0]["message"]["content"])
        
        # DEBUG: Print the AI analysis to see what we're getting
        print(f"DEBUG: AI Analysis for batch {batch_num + 1}:", file=sys.stderr)
        print(f"  Frame details count: {len(ai_analysis.get('frameDetails', []))}", file=sys.stderr)
        for i, frame_detail in enumerate(ai_analysis.get('frameDetails', [])):
            safety_issues = frame_detail.get('safetyIssues', [])
            print(f"  Frame {i}: {len(safety_issues)} safety issues", file=sys.stderr)
            for j, issue in enumerate(safety_issues):
                grid_cells = issue.get('gridCells', 'None')
                print(f"    Issue {j}: type={issue.get('type')}, gridCells='{grid_cells}'", file=sys.stderr)
        
        return {
            "success": True,
            "analysis": ai_analysis
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Batch analysis error: {str(e)}"
        }

def analyze_frames_with_openrouter(frames_dir, api_key, job_id):
    """
    Analyze extracted frames using OpenRouter GPT-4o API
    """
    try:
        # Dataset caching configuration via optional CLI/env
        dataset_root = os.environ.get('DATASET_ROOT')
        video_path = os.environ.get('VIDEO_PATH')
        if hasattr(analyze_frames_with_openrouter, "_options"):
            opts = getattr(analyze_frames_with_openrouter, "_options")
            if opts.get("dataset_root"):
                dataset_root = opts["dataset_root"]
            if opts.get("video_path"):
                video_path = opts["video_path"]

        # Default dataset root if not provided
        if not dataset_root:
            dataset_root = "datasets"

        dataset_dir = None
        if dataset_root:
            # Derive dataset name: prefer video basename, else frames dir, else job id
            if video_path:
                base_name = os.path.splitext(os.path.basename(video_path))[0]
            else:
                base_name = os.path.basename(os.path.abspath(frames_dir)) or job_id
            safe_name = "".join(c if c.isalnum() or c in ("-","_",".") else "_" for c in base_name)
            dataset_dir = os.path.join(dataset_root, safe_name)
            images_dir = os.path.join(dataset_dir, "images")
            os.makedirs(images_dir, exist_ok=True)

            # Early return if cached analysis exists
            cached_analysis_path = os.path.join(dataset_dir, "analysis.json")
            if os.path.exists(cached_analysis_path):
                try:
                    with open(cached_analysis_path, "r", encoding="utf-8") as f:
                        cached = json.load(f)
                    print(f"Using cached analysis at {cached_analysis_path}", file=sys.stderr)
                    return cached
                except Exception as e:
                    print(f"Failed to read cached analysis, recomputing: {e}", file=sys.stderr)
        # Find all frame files in the directory
        frame_files = []
        for file in os.listdir(frames_dir):
            if file.startswith('frame_') and file.endswith('.jpg'):
                frame_files.append(file)
        
        frame_files.sort()  # Sort by filename to maintain order
        
        if not frame_files:
            return {
                "success": False,
                "error": "No frame files found in directory",
                "frames_checked": 0
            }
        
        print(f"Found {len(frame_files)} frame files to analyze", file=sys.stderr)
        
        # Step 1: Filter out similar frames with balanced similarity detection
        print("Step 1: Filtering out similar frames (balanced mode)...", file=sys.stderr)
        unique_frame_files = filter_unique_frames(frame_files, frames_dir, similarity_threshold=0.88)
        
        # Additional safety check: if we still have too many frames, force more aggressive sampling
        if len(unique_frame_files) > 15:
            print(f"Still {len(unique_frame_files)} frames after filtering - applying additional time-based sampling", file=sys.stderr)
            step = max(2, len(unique_frame_files) // 10)  # Max 10 frames (increased from 6)
            unique_frame_files = unique_frame_files[::step][:10]
            print(f"Final frame count after additional sampling: {len(unique_frame_files)}", file=sys.stderr)
        
        # Step 2: Convert unique frames to base64
        print("Step 2: Loading unique frames...", file=sys.stderr)
        frames_data = []
        for idx, filename in enumerate(unique_frame_files):
            filepath = os.path.join(frames_dir, filename)
            try:
                with open(filepath, 'rb') as f:
                    image_data = f.read()
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    
                    # Extract timestamp from filename (frame_X_XXmXXs.jpg)
                    parts = filename.replace('.jpg', '').split('_')
                    timestamp = parts[2] if len(parts) > 2 else "00:00"
                    
                    frames_data.append({
                        "filename": filename,
                        "timestamp": timestamp,
                        "image_base64": image_base64,
                        "original_index": idx
                    })
                    
                print(f"Loaded unique frame: {filename} ({len(image_data)} bytes)", file=sys.stderr)
                    
            except Exception as e:
                print(f"Failed to load frame {filename}: {e}", file=sys.stderr)
                continue
        
        if not frames_data:
            return {
                "success": False,
                "error": "No frames could be loaded for analysis",
                "frames_checked": len(frame_files),
                "unique_frames": len(unique_frame_files)
            }
        
        print(f"Step 3: Processing {len(frames_data)} unique frames in batches with detection integration...", file=sys.stderr)
        
        # Step 3: Process frames in smaller batches for efficiency with YOLO detection
        batch_size = min(3, max(1, len(frames_data) // 2))  # Dynamic batch size based on frame count
        print(f"Using batch size: {batch_size} for {len(frames_data)} frames", file=sys.stderr)
        all_frame_details, all_yolo_detections = process_frames_in_batches(frames_data, api_key, batch_size=batch_size, frames_dir=frames_dir)
        
        # Step 4: Combine results and determine overall safety status with enhanced bounding boxes
        overall_incorrect_parking = False
        overall_waste_material = False
        all_explanations = []
        processed_frames = []
        comprehensive_mitigations = []
        
        # Create frame objects with enhanced bounding boxes (combining YOLO and AI detections)
        for frame_idx, frame_detail in enumerate(all_frame_details):
            frame_index = frame_detail.get('frameIndex', 0)
            timestamp = frame_detail.get('timestamp', '00:00')
            
            # Find corresponding frame data and YOLO detections
            corresponding_frame = None
            frame_yolo_detections = []
            
            for frame_data in frames_data:
                if frame_data['original_index'] == frame_index:
                    corresponding_frame = frame_data
                    if frame_idx < len(all_yolo_detections):
                        frame_yolo_detections = all_yolo_detections[frame_idx]
                    break
            
            if corresponding_frame:
                # Create enhanced bounding boxes combining AI grid detection and YOLO precision
                bounding_boxes = []
                
                # Process AI-detected safety issues with grid-based locations
                if frame_detail.get("safetyIssues"):
                    for issue in frame_detail["safetyIssues"]:
                        if issue.get("type") in ["parking", "vehicle"]:
                            overall_incorrect_parking = True
                        elif issue.get("type") in ["waste", "debris"]:
                            overall_waste_material = True
                        
                        all_explanations.append(f"Frame {frame_index}: {issue.get('description', '')}")
                        
                        # Convert grid cells to bounding box coordinates
                        grid_cells = issue.get('gridCells', '')
                        bbox_coords = convert_grid_cells_to_bounding_box(grid_cells)
                        
                        if bbox_coords:
                            bounding_boxes.append({
                                "label": f"AI: {issue.get('type', 'hazard')}: {issue.get('description', '')[:40]}...",
                                "x": bbox_coords['x'],
                                "y": bbox_coords['y'],
                                "w": bbox_coords['w'],
                                "h": bbox_coords['h'],
                                "source": "ai_analysis",
                                "severity": issue.get('severity', 'medium'),
                                "mitigation": issue.get('mitigationStrategy', 'No specific mitigation provided')
                            })
                            print(f"AI Grid cells '{grid_cells}' -> bbox: x={bbox_coords['x']:.3f}, y={bbox_coords['y']:.3f}, w={bbox_coords['w']:.3f}, h={bbox_coords['h']:.3f}", file=sys.stderr)
                
                # Add only CRITICAL detector hazards as precise bounding boxes
                for yolo_obj in frame_yolo_detections:
                    bbox = yolo_obj['bbox']
                    
                    # Apply smart filtering - only show critical hazards
                    if is_critical_safety_hazard(yolo_obj['class_name'], yolo_obj['confidence'], bbox):
                        severity_info = assess_hazard_severity(yolo_obj['class_name'], yolo_obj['confidence'], bbox)
                        
                        # Create enhanced bounding box with hazard details
                        hazard_bbox = {
                            "label": f"{yolo_obj['class_name'].title()} - {severity_info['severity'].upper()}",
                            "x": bbox['x'],
                            "y": bbox['y'],
                            "w": bbox['w'],
                            "h": bbox['h'],
                            "source": "yolo_detection",
                            "confidence": yolo_obj['confidence'],
                            "safety_category": yolo_obj['safety_category'],
                            "severity": severity_info['severity'],
                            "reason": severity_info['reason'],
                            "priority": severity_info['priority'],
                            "immediate_action": severity_info['immediate_action'],
                            "hazard_type": "pathway_obstruction",
                            "mitigation_summary": f"Remove {yolo_obj['class_name']} from pathway immediately" if severity_info['immediate_action'] else f"Relocate {yolo_obj['class_name']} to designated area"
                        }
                        bounding_boxes.append(hazard_bbox)
                        print(f"CRITICAL HAZARD: '{yolo_obj['class_name']}' ({severity_info['severity']}) -> bbox: x={bbox['x']:.3f}, y={bbox['y']:.3f}, w={bbox['w']:.3f}, h={bbox['h']:.3f}", file=sys.stderr)
                
                # Create frame object for frontend with enhanced data
                frame_obj = {
                    "time": timestamp,
                    "imageUrl": f"/temp/{corresponding_frame['filename']}",
                    "filename": corresponding_frame['filename'],
                    "boundingBoxes": bounding_boxes,
                    "yolo_detections": len(frame_yolo_detections),
                    "ai_issues": len(frame_detail.get("safetyIssues", [])),
                    "frame_analysis": {
                        "detailed_observations": frame_detail.get('detailedObservations', ''),
                        "pathway_clearance": frame_detail.get('pathwayClearance', ''),
                        "emergency_access": frame_detail.get('emergencyAccess', ''),
                        "recommended_actions": frame_detail.get('recommendedActions', [])
                    }
                }
                processed_frames.append(frame_obj)
        
        # Generate comprehensive mitigation strategies
        print("Generating comprehensive mitigation strategies...", file=sys.stderr)
        flat_yolo_detections = [obj for frame_detections in all_yolo_detections for obj in frame_detections]
        ai_analysis_summary = {
            "incorrectParking": overall_incorrect_parking,
            "wasteMaterial": overall_waste_material
        }
        comprehensive_mitigations = generate_mitigation_strategies(flat_yolo_detections, ai_analysis_summary)
        
        combined_explanation = f"Comprehensive analysis of {len(frames_data)} unique frames using combined YOLO object detection and AI grid-based analysis (filtered from {len(frame_files)} total frames). " + "; ".join(all_explanations) if all_explanations else f"Analyzed {len(frames_data)} unique frames - no safety violations detected."
        
        print(f"Analysis complete: {len(all_frame_details)} frames analyzed with {len(flat_yolo_detections)} detected objects", file=sys.stderr)
        
        # Calculate comprehensive statistics
        total_yolo_objects = len(flat_yolo_detections)
        total_hazardous_objects = len([obj for obj in flat_yolo_detections if obj.get('potential_hazard', False)])
        total_ai_issues = sum(len(frame_detail.get("safetyIssues", [])) for frame_detail in all_frame_details)
        
        # Build final result object
        result_obj = {
            "success": True,
            "analysis": {
                "incorrectParking": overall_incorrect_parking,
                "wasteMaterial": overall_waste_material,
                "explanation": combined_explanation,
                "frameDetails": all_frame_details,
                "frames": processed_frames,  # Enhanced bounding boxes combining YOLO and AI
                "mitigationStrategies": comprehensive_mitigations,  # Comprehensive mitigation plans
                "violations": [],  # Legacy field for compatibility
                "statistics": {
                    "total_frames_analyzed": len(frames_data),
                    "total_yolo_objects": total_yolo_objects,
                    "total_hazardous_objects": total_hazardous_objects,
                    "total_ai_safety_issues": total_ai_issues,
                    "frames_with_issues": len([f for f in processed_frames if len(f['boundingBoxes']) > 0])
                }
            },
            "frames_analyzed": len(frames_data),
            "total_frames": len(frame_files),
            "unique_frames": len(unique_frame_files),
            "similarity_filtered": len(frame_files) - len(unique_frame_files),
            "yolo_detections": total_yolo_objects,
            "hazardous_objects": total_hazardous_objects,
            "method": "Enhanced Detection (Vision + Grid Analysis)",
            "detection_methods": {
                "yolo_available": HAS_YOLO,
                "ai_grid_analysis": True,
                "similarity_filtering": True
            }
        }

        # Helper: draw bounding boxes and labels on an image
        def _annotate_and_save_image(src_path, boxes, dst_path):
            try:
                img = cv2.imread(src_path)
                if img is None:
                    return False
                height, width = img.shape[:2]

                # Define colors
                color_ai = (40, 180, 240)      # Orange-ish (BGR)
                color_yolo = (20, 200, 20)     # Green
                color_critical = (0, 0, 255)   # Red
                color_high = (0, 165, 255)     # Orange
                color_medium = (0, 255, 255)   # Yellow
                color_low = (255, 255, 0)      # Cyan

                for b in boxes:
                    x = int(b.get('x', 0) * width)
                    y = int(b.get('y', 0) * height)
                    w = int(b.get('w', 0) * width)
                    h = int(b.get('h', 0) * height)
                    x2, y2 = x + w, y + h

                    source = b.get('source', 'ai_analysis')
                    severity = (b.get('severity') or '').lower()

                    # Choose color based on severity first
                    if severity == 'critical':
                        color = color_critical
                    elif severity == 'high':
                        color = color_high
                    elif severity == 'medium':
                        color = color_medium
                    elif severity == 'low':
                        color = color_low
                    else:
                        color = color_yolo if source == 'yolo_detection' else color_ai

                    # Draw rectangle
                    cv2.rectangle(img, (x, y), (x2, y2), color, 2)

                    # Label text
                    label = b.get('label') or b.get('hazard_type') or 'object'
                    conf = b.get('confidence')
                    if isinstance(conf, (int, float)):
                        label = f"{label} ({conf:.2f})"

                    # Put label with background
                    (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(img, (x, max(0, y - th - 6)), (x + tw + 6, y), color, -1)
                    cv2.putText(img, label, (x + 3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

                # Save as PNG for quality
                return cv2.imwrite(dst_path, img)
            except Exception as _e:
                print(f"Annotate save failed for {src_path} -> {dst_path}: {_e}", file=sys.stderr)
                return False

        # Persist dataset if configured
        if dataset_dir:
            try:
                # Save analysis.json
                analysis_path = os.path.join(dataset_dir, "analysis.json")
                with open(analysis_path, "w", encoding="utf-8") as f:
                    json.dump(result_obj, f, ensure_ascii=False)

                # Write annotated images into dataset/images
                images_dir = os.path.join(dataset_dir, "images")
                os.makedirs(images_dir, exist_ok=True)
                # Build quick lookup map from filename to boxes
                filename_to_boxes = {}
                for pf in processed_frames:
                    fn = pf.get('filename')
                    if fn:
                        filename_to_boxes[fn] = pf.get('boundingBoxes', [])
                for filename in unique_frame_files:
                    src = os.path.join(frames_dir, filename)
                    # Save annotated as PNG to preserve quality
                    out_name = os.path.splitext(filename)[0] + ".png"
                    dst = os.path.join(images_dir, out_name)
                    boxes = filename_to_boxes.get(filename, [])
                    ok = _annotate_and_save_image(src, boxes, dst)
                    if not ok and os.path.exists(src):
                        # Fallback to copy original
                        shutil.copy2(src, os.path.join(images_dir, filename))

                # Save metadata.json
                metadata = {
                    "video_path": video_path,
                    "frames_source_dir": os.path.abspath(frames_dir),
                    "dataset_dir": os.path.abspath(dataset_dir),
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "job_id": job_id,
                    "unique_frame_files": unique_frame_files,
                    "image_format": "png",
                    "detection_methods": result_obj["detection_methods"],
                    "stats": result_obj["analysis"]["statistics"]
                }
                with open(os.path.join(dataset_dir, "metadata.json"), "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False)

                # Update datasets index
                index_path = os.path.join(dataset_root, "index.json")
                index = {}
                if os.path.exists(index_path):
                    try:
                        with open(index_path, "r", encoding="utf-8") as f:
                            index = json.load(f)
                    except Exception:
                        index = {}
                index[safe_name] = {
                    "video_path": video_path,
                    "dataset_dir": os.path.abspath(dataset_dir),
                    "analysis_path": os.path.abspath(analysis_path),
                    "images_dir": os.path.abspath(images_dir),
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                }
                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index, f, ensure_ascii=False)
                print(f"Saved dataset to {dataset_dir}", file=sys.stderr)
            except Exception as e:
                print(f"Failed to persist dataset: {e}", file=sys.stderr)

        # Return the result object
        return result_obj
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "OpenRouter API request timed out",
            "frames_analyzed": len(frames_data) if 'frames_data' in locals() else 0
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Network error: {str(e)}",
            "frames_analyzed": len(frames_data) if 'frames_data' in locals() else 0
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse API response as JSON: {str(e)}",
            "frames_analyzed": len(frames_data) if 'frames_data' in locals() else 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "frames_analyzed": len(frames_data) if 'frames_data' in locals() else 0
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze frames with OpenRouter and cache dataset")
    parser.add_argument("frames_directory", help="Directory containing frame_*.jpg files")
    parser.add_argument("api_key", help="OpenRouter API key")
    parser.add_argument("job_id", help="Job id for tracking")
    parser.add_argument("--dataset-root", dest="dataset_root", default=None, help="Root directory to save datasets")
    parser.add_argument("--video-path", dest="video_path", default=None, help="Original video file path (to name dataset)")
    args = parser.parse_args()

    frames_dir = args.frames_directory
    api_key = args.api_key
    job_id = args.job_id

    if not os.path.exists(frames_dir):
        print(json.dumps({
            "success": False,
            "error": f"Frames directory does not exist: {frames_dir}"
        }))
        sys.exit(1)

    if not api_key:
        print(json.dumps({
            "success": False,
            "error": "OpenRouter API key is required"
        }))
        sys.exit(1)

    # Pass optional settings to the function via attribute to avoid refactor
    setattr(analyze_frames_with_openrouter, "_options", {
        "dataset_root": args.dataset_root,
        "video_path": args.video_path
    })

    result = analyze_frames_with_openrouter(frames_dir, api_key, job_id)
    print(json.dumps(result))
