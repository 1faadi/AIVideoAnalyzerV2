import { type NextRequest, NextResponse } from "next/server"
import { createJob, getJob, updateJobStatus } from "../../../lib/job-manager"
import fs from "fs"
import path from "path"

// In-memory storage for video data (in production, use a database or file storage)
const videoStorage = new Map<string, ArrayBuffer>()


export async function POST(request: NextRequest) {
  try {
    console.log("[v0] Upload API called")

    const formData = await request.formData()
    const file = formData.get("video") as File

    if (!file) {
      console.log("[v0] No file in form data")
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 })
    }

    console.log("[v0] File received:", file.name, file.type, file.size)

    // Validate file type
    if (!file.type.startsWith("video/")) {
      console.log("[v0] Invalid file type:", file.type)
      return NextResponse.json({ error: "File must be a video" }, { status: 400 })
    }

    // Check file size (limit to 100MB)
    if (file.size > 100 * 1024 * 1024) {
      console.log("[v0] File too large:", file.size)
      return NextResponse.json({ error: "File too large (max 100MB)" }, { status: 400 })
    }

    // Create new job
    const jobId = createJob(file.name)
    console.log("[v0] Generated job ID:", jobId)

    // Store video data in memory (for processing)
    const videoData = await file.arrayBuffer()
    console.log("[v0] Video data loaded, size:", videoData.byteLength)
    
    // Store video data for processing
    videoStorage.set(jobId, videoData)
    
    // Save video file to public/temp directory for processing
    const tempDir = path.join(process.cwd(), "public", "temp")
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true })
    }
    
    const tempVideoPath = path.join(tempDir, `video_${jobId}_${file.name.replace(/[^a-zA-Z0-9.]/g, '_')}`)
    fs.writeFileSync(tempVideoPath, Buffer.from(videoData))
    console.log("[v0] Video saved to:", tempVideoPath)

    // Set status to pending - processing will start when user clicks the button
    updateJobStatus(jobId, 'pending')
    console.log("[v0] Video uploaded successfully, ready for processing")

    return NextResponse.json({
      success: true,
      jobId,
      message: "Video uploaded successfully",
      tempPath: tempVideoPath
    })
  } catch (error) {
    console.error("[v0] Upload error:", error)

    // Provide more specific error information
    if (error instanceof Error) {
      return NextResponse.json(
        {
          error: `Upload failed: ${error.message}`,
        },
        { status: 500 },
      )
    }

    return NextResponse.json(
      {
        error: "Upload failed due to unknown error",
      },
      { status: 500 },
    )
  }
}

// Export video storage for other API routes to access
export { videoStorage }
