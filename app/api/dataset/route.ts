import { NextResponse } from "next/server"
import path from "path"
import fs from "fs"

export async function GET() {
  try {
    const datasetDir = path.join(process.cwd(), "datasets", "temp")
    const analysisPath = path.join(datasetDir, "analysis.json")

    if (!fs.existsSync(analysisPath)) {
      return NextResponse.json({ error: "Dataset not found" }, { status: 404 })
    }

    const raw = fs.readFileSync(analysisPath, "utf-8")
    const analysis = JSON.parse(raw)

    // Ensure images are available under public for static serving
    const srcImagesDir = path.join(datasetDir, "images")
    const publicImagesDir = path.join(process.cwd(), "public", "datasets", "temp", "images")
    fs.mkdirSync(publicImagesDir, { recursive: true })
    if (fs.existsSync(srcImagesDir)) {
      for (const file of fs.readdirSync(srcImagesDir)) {
        const src = path.join(srcImagesDir, file)
        const dst = path.join(publicImagesDir, file)
        if (!fs.existsSync(dst)) {
          fs.copyFileSync(src, dst)
        }
      }
    }

    const frames = (analysis.analysis?.frames || []).map((f: any) => {
      const filename: string | undefined = f.filename
      const pngName = filename ? `${filename.replace(/\.jpg$/i, "")}.png` : undefined
      const finalUrl = pngName ? `/datasets/temp/images/${pngName}` : (f.imageUrl || "/temp/unknown.jpg")
      return { ...f, imageUrl: finalUrl }
    })

    const response = {
      incorrectParking: analysis.analysis?.incorrectParking || false,
      wasteMaterial: analysis.analysis?.wasteMaterial || false,
      explanation: analysis.analysis?.explanation || "Cached analysis loaded",
      frames,
      frameDetails: analysis.analysis?.frameDetails || [],
      mitigationStrategies: analysis.analysis?.mitigationStrategies || []
    }

    return NextResponse.json(response)
  } catch (error) {
    return NextResponse.json({ error: "Failed to load dataset" }, { status: 500 })
  }
}


