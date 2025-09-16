"use client"

import { useEffect, useRef, useState } from "react"

interface BoundingBox {
  label: string
  x: number
  y: number
  w: number
  h: number
  severity?: string
  reason?: string
  immediate_action?: boolean
  mitigation_summary?: string
  confidence?: number
  source?: string
}

interface AnnotatedImageProps {
  src: string
  alt: string
  boundingBoxes: BoundingBox[]
}

export function AnnotatedImage({ src, alt, boundingBoxes }: AnnotatedImageProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)
  const [imageLoaded, setImageLoaded] = useState(false)

  useEffect(() => {
    if (imageLoaded && canvasRef.current && imageRef.current) {
      drawAnnotations()
    }
  }, [imageLoaded, boundingBoxes])

  const drawAnnotations = () => {
    const canvas = canvasRef.current
    const image = imageRef.current
    if (!canvas || !image) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas size to match image
    canvas.width = image.naturalWidth
    canvas.height = image.naturalHeight

    // Draw the image
    ctx.drawImage(image, 0, 0)

    // Draw bounding boxes with severity-based colors
    boundingBoxes.forEach((box, index) => {
      const x = box.x * canvas.width
      const y = box.y * canvas.height
      const width = box.w * canvas.width
      const height = box.h * canvas.height

      // Color coding based on severity
      let strokeColor = "#dc2626" // default red
      let fillColor = "#dc2626"
      let lineWidth = 3

      switch (box.severity) {
        case "critical":
          strokeColor = "#dc2626" // red
          fillColor = "#dc2626"
          lineWidth = 4
          break
        case "high":
          strokeColor = "#ea580c" // orange
          fillColor = "#ea580c"
          lineWidth = 3
          break
        case "medium":
          strokeColor = "#d97706" // yellow-orange
          fillColor = "#d97706"
          lineWidth = 2
          break
        case "low":
          strokeColor = "#16a34a" // green
          fillColor = "#16a34a"
          lineWidth = 2
          break
      }

      // Draw rectangle with pulsing effect for immediate action items
      if (box.immediate_action) {
        ctx.shadowColor = strokeColor
        ctx.shadowBlur = 10
      }
      
      ctx.strokeStyle = strokeColor
      ctx.lineWidth = lineWidth
      ctx.strokeRect(x, y, width, height)
      
      // Reset shadow
      ctx.shadowBlur = 0

      // Create compact but informative label
      const labelText = box.severity ? 
        `${box.label.split(" - ")[0]} (${box.severity.toUpperCase()})` : 
        box.label.replace("_", " ")
      
      ctx.font = "bold 14px sans-serif"
      const textMetrics = ctx.measureText(labelText)
      const labelWidth = Math.min(textMetrics.width + 12, width - 4) // Don't exceed box width
      const labelHeight = 22

      // Draw label background with transparency
      ctx.fillStyle = fillColor
      ctx.globalAlpha = 0.9
      ctx.fillRect(x, y - labelHeight, labelWidth, labelHeight)
      ctx.globalAlpha = 1.0

      // Draw label text
      ctx.fillStyle = "white"
      ctx.fillText(labelText, x + 6, y - 6)

      // Add urgency indicator for immediate action items
      if (box.immediate_action) {
        ctx.fillStyle = "#fbbf24" // yellow warning
        ctx.beginPath()
        ctx.arc(x + width - 15, y + 15, 8, 0, 2 * Math.PI)
        ctx.fill()
        
        // Add exclamation mark
        ctx.fillStyle = "#000"
        ctx.font = "bold 12px sans-serif"
        ctx.fillText("!", x + width - 18, y + 19)
      }
    })
  }

  const handleImageLoad = () => {
    setImageLoaded(true)
  }

  return (
    <div className="relative border border-border rounded-lg overflow-hidden bg-muted">
      <img
        ref={imageRef}
        src={src || "/placeholder.svg"}
        alt={alt}
        onLoad={handleImageLoad}
        className="w-full h-auto"
        style={{ display: imageLoaded ? "block" : "none" }}
      />
      {imageLoaded && (
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-auto"
          style={{ maxWidth: "100%", height: "auto" }}
        />
      )}
      {!imageLoaded && (
        <div className="aspect-video flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      )}
    </div>
  )
}
