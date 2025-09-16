#!/usr/bin/env python3
"""
Test script for the enhanced warehouse safety analysis pipeline
This script demonstrates the complete workflow with YOLO integration and comprehensive analysis
"""

import os
import sys
import json
import tempfile
from pathlib import Path

def test_enhanced_pipeline():
    """
    Test the complete enhanced pipeline
    """
    print("=== Enhanced Warehouse Safety Analysis Pipeline Test ===\n")
    
    # Configuration
    test_video = "test_video.mp4"  # Replace with actual test video path
    output_dir = tempfile.mkdtemp(prefix="warehouse_test_")
    api_key = "your_openrouter_api_key"  # Replace with actual API key
    job_id = "test_job_001"
    
    print(f"Test configuration:")
    print(f"  Video path: {test_video}")
    print(f"  Output directory: {output_dir}")
    print(f"  Job ID: {job_id}")
    print()
    
    # Step 1: Enhanced Frame Extraction with Real-time Similarity Checking
    print("Step 1: Enhanced Frame Extraction")
    print("-" * 40)
    
    if os.path.exists(test_video):
        try:
            # Import the enhanced extraction function
            sys.path.append(os.path.dirname(__file__))
            from extract_frames_opencv import extract_frames_with_opencv
            
            print("Running enhanced frame extraction with similarity checking...")
            extraction_result = extract_frames_with_opencv(
                video_path=test_video,
                output_dir=output_dir,
                frame_interval=1,
                similarity_threshold=0.80
            )
            
            if extraction_result.get("success"):
                total_extracted = extraction_result.get("total_frames_extracted", 0)
                frames_skipped = extraction_result.get("frames_skipped", 0)
                similarity_threshold = extraction_result.get("similarity_threshold", 0.85)
                
                print(f"✓ Frame extraction successful!")
                print(f"  Frames extracted: {total_extracted}")
                print(f"  Frames skipped (similar): {frames_skipped}")
                print(f"  Similarity threshold: {similarity_threshold}")
                print(f"  Method: {extraction_result.get('video_info', {}).get('method', 'unknown')}")
            else:
                print(f"✗ Frame extraction failed: {extraction_result.get('error')}")
                return False
                
        except Exception as e:
            print(f"✗ Error during frame extraction: {e}")
            return False
    else:
        print(f"⚠ Test video not found: {test_video}")
        print("Skipping frame extraction test...")
        return False
    
    print()
    
    # Step 2: Enhanced Analysis with YOLO + AI Integration
    print("Step 2: Enhanced Analysis (YOLO + AI)")
    print("-" * 40)
    
    try:
        # Import the enhanced analysis function
        from analyze_frames_openrouter import analyze_frames_with_openrouter
        
        print("Running comprehensive analysis with YOLO integration...")
        analysis_result = analyze_frames_with_openrouter(
            frames_dir=output_dir,
            api_key=api_key,
            job_id=job_id
        )
        
        if analysis_result.get("success"):
            analysis = analysis_result.get("analysis", {})
            detection_methods = analysis_result.get("detection_methods", {})
            statistics = analysis.get("statistics", {})
            
            print(f"✓ Analysis successful!")
            print(f"  Method: {analysis_result.get('method', 'unknown')}")
            print(f"  YOLO available: {detection_methods.get('yolo_available', False)}")
            print(f"  AI grid analysis: {detection_methods.get('ai_grid_analysis', False)}")
            print(f"  Similarity filtering: {detection_methods.get('similarity_filtering', False)}")
            print()
            
            print("Analysis Statistics:")
            print(f"  Total frames analyzed: {statistics.get('total_frames_analyzed', 0)}")
            print(f"  Total YOLO objects: {statistics.get('total_yolo_objects', 0)}")
            print(f"  Hazardous objects: {statistics.get('total_hazardous_objects', 0)}")
            print(f"  AI safety issues: {statistics.get('total_ai_safety_issues', 0)}")
            print(f"  Frames with issues: {statistics.get('frames_with_issues', 0)}")
            print()
            
            print("Safety Assessment:")
            print(f"  Incorrect parking detected: {analysis.get('incorrectParking', False)}")
            print(f"  Waste material detected: {analysis.get('wasteMaterial', False)}")
            print()
            
            # Display comprehensive mitigation strategies
            mitigations = analysis.get("mitigationStrategies", [])
            if mitigations:
                print("Comprehensive Mitigation Strategies:")
                for i, mitigation in enumerate(mitigations, 1):
                    print(f"\n  {i}. {mitigation.get('type', 'Unknown').upper()}")
                    print(f"     Severity: {mitigation.get('severity', 'unknown').upper()}")
                    print(f"     Urgency: {mitigation.get('urgency', 'unknown')}")
                    print(f"     Description: {mitigation.get('description', 'No description')}")
                    
                    # Display specific risks
                    risks = mitigation.get('specific_risks', [])
                    if risks:
                        print(f"     Specific Risks:")
                        for risk in risks:
                            print(f"       - {risk}")
                    
                    # Display mitigation steps
                    steps = mitigation.get('mitigation_steps', [])
                    if steps:
                        print(f"     Mitigation Steps:")
                        for step in steps:
                            print(f"       - {step}")
                    
                    print(f"     Timeline: {mitigation.get('timeline', 'Not specified')}")
                    print(f"     Responsible Party: {mitigation.get('responsible_party', 'Not specified')}")
                    print(f"     Estimated Cost: {mitigation.get('estimated_cost', 'Not specified')}")
                    print(f"     Emergency Impact: {mitigation.get('emergency_impact', 'No impact assessed')}")
                    
                    compliance = mitigation.get('compliance')
                    if compliance:
                        print(f"     Compliance: {compliance}")
                    print()
            else:
                print("No specific mitigation strategies generated.")
            
            # Display frame-level analysis summary
            frames = analysis.get("frames", [])
            if frames:
                print("Frame Analysis Summary:")
                for frame in frames:
                    bboxes = frame.get("boundingBoxes", [])
                    yolo_count = frame.get("yolo_detections", 0)
                    ai_count = frame.get("ai_issues", 0)
                    
                    print(f"  Frame {frame.get('time', 'unknown')}: {len(bboxes)} bounding boxes")
                    print(f"    YOLO detections: {yolo_count}, AI issues: {ai_count}")
                    
                    for bbox in bboxes[:3]:  # Show first 3 bounding boxes
                        source = bbox.get("source", "unknown")
                        label = bbox.get("label", "No label")[:60] + "..."
                        print(f"    - [{source}] {label}")
                    
                    if len(bboxes) > 3:
                        print(f"    ... and {len(bboxes) - 3} more")
                    print()
            
        else:
            print(f"✗ Analysis failed: {analysis_result.get('error')}")
            return False
            
    except Exception as e:
        print(f"✗ Error during analysis: {e}")
        return False
    
    print()
    
    # Step 3: Results Summary
    print("Step 3: Pipeline Results Summary")
    print("-" * 40)
    
    print("✓ Enhanced pipeline test completed successfully!")
    print()
    print("Pipeline Features Demonstrated:")
    print("  ✓ Real-time similarity checking during frame extraction")
    print("  ✓ YOLO object detection integration")
    print("  ✓ AI-powered comprehensive safety analysis")
    print("  ✓ Enhanced bounding box accuracy (YOLO + AI grid)")
    print("  ✓ Comprehensive mitigation strategy generation")
    print("  ✓ Detailed statistics and reporting")
    print()
    
    print("Key Improvements:")
    print("  • Faster frame sampling (1 second intervals) with real-time similarity filtering")
    print("  • Enhanced YOLO detection with multiple models and lower confidence thresholds")
    print("  • Comprehensive object detection covering all potential hazards")
    print("  • Detailed mitigation strategies with specific timelines and cost estimates")
    print("  • Enhanced bounding box accuracy with dual-source detection")
    print("  • Comprehensive risk assessment and compliance checking")
    print("  • Detailed frame-level analysis with actionable recommendations")
    
    return True

def display_requirements():
    """
    Display system requirements for the enhanced pipeline
    """
    print("=== System Requirements ===\n")
    print("Required Python packages:")
    print("  • opencv-python>=4.8.0")
    print("  • numpy>=1.24.0")
    print("  • requests>=2.28.0")
    print("  • scikit-image>=0.21.0 (for advanced similarity detection)")
    print("  • ultralytics>=8.0.0 (for YOLO object detection)")
    print("  • Pillow>=10.0.0")
    print()
    print("Hardware recommendations:")
    print("  • GPU with CUDA support (for faster YOLO inference)")
    print("  • Minimum 8GB RAM")
    print("  • SSD storage for faster frame processing")
    print()
    print("API Requirements:")
    print("  • OpenRouter API key for AI analysis")
    print("  • Internet connection for API calls")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--requirements":
        display_requirements()
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Enhanced Warehouse Safety Analysis Pipeline Test")
        print()
        print("Usage:")
        print("  python test_enhanced_pipeline.py           # Run full pipeline test")
        print("  python test_enhanced_pipeline.py --requirements  # Show requirements")
        print("  python test_enhanced_pipeline.py --help          # Show this help")
        print()
        print("Before running the test:")
        print("1. Update the test_video path in the script")
        print("2. Set your OpenRouter API key")
        print("3. Install required dependencies: pip install -r requirements.txt")
    else:
        print("Note: This is a demonstration script.")
        print("Update the test_video path and API key before running.")
        print("Use --help for more information.")
        # Uncomment the line below to run the actual test
        # test_enhanced_pipeline()
