import { type NextRequest, NextResponse } from "next/server"
import { getJob } from "../../../../lib/job-manager"

export async function GET(request: NextRequest, { params }: { params: { id: string } }) {
  try {
    console.log("[v0] Job status API called for ID:", params.id)

    const jobId = params.id
    const job = getJob(jobId)

    if (!job) {
      console.log("[v0] Job not found:", jobId)
      return NextResponse.json({ error: "Job not found" }, { status: 404 })
    }

    console.log("[v0] Job status retrieved:", job.status)
    const response = {
      id: job.id,
      status: job.status,
      filename: job.filename,
      uploadedAt: job.uploadedAt,
      results: job.results,
    }
    console.log("[v0] Returning job status:", response)

    return NextResponse.json(response)
  } catch (error) {
    console.error("[v0] Job status error:", error)
    return NextResponse.json({ error: "Failed to get job status" }, { status: 500 })
  }
}
