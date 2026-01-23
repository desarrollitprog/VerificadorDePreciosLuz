package com.example.verificadordepreciosluz.ui.scanner

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View
import androidx.core.content.ContextCompat
import com.example.verificadordepreciosluz.R

class ScanOverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyle: Int = 0
) : View(context, attrs, defStyle) {

    private val framePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 4f
        color = ContextCompat.getColor(context, android.R.color.white)
    }

    private val cornerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 6f
        color = ContextCompat.getColor(context, R.color.naranja_luz)
    }

    private val guideRect = RectF()

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()
        if (w <= 0f || h <= 0f) return

        // Caja guía en formato horizontal (1D barcodes)
        val boxWidth = w * 0.8f
        val boxHeight = h * 0.22f
        val left = (w - boxWidth) / 2f
        val top = (h - boxHeight) / 2f
        guideRect.set(left, top, left + boxWidth, top + boxHeight)

        val radius = 24f
        canvas.drawRoundRect(guideRect, radius, radius, framePaint)

        val cl = 32f // longitud de esquina
        // Esquinas superiores
        canvas.drawLine(guideRect.left, guideRect.top, guideRect.left + cl, guideRect.top, cornerPaint)
        canvas.drawLine(guideRect.left, guideRect.top, guideRect.left, guideRect.top + cl, cornerPaint)
        canvas.drawLine(guideRect.right, guideRect.top, guideRect.right - cl, guideRect.top, cornerPaint)
        canvas.drawLine(guideRect.right, guideRect.top, guideRect.right, guideRect.top + cl, cornerPaint)
        // Esquinas inferiores
        canvas.drawLine(guideRect.left, guideRect.bottom, guideRect.left + cl, guideRect.bottom, cornerPaint)
        canvas.drawLine(guideRect.left, guideRect.bottom, guideRect.left, guideRect.bottom - cl, cornerPaint)
        canvas.drawLine(guideRect.right, guideRect.bottom, guideRect.right - cl, guideRect.bottom, cornerPaint)
        canvas.drawLine(guideRect.right, guideRect.bottom, guideRect.right, guideRect.bottom - cl, cornerPaint)
    }
}
