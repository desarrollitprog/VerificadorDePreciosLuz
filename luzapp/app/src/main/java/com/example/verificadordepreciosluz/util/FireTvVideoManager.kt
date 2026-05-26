package com.example.verificadordepreciosluz.util

import android.media.MediaPlayer
import android.net.Uri
import android.util.Log
import android.view.SurfaceHolder
import android.widget.VideoView

/**
 * Maneja el ciclo de vida del VideoView específico para Fire TV.
 * Detecta destrucción/recreación de la Surface nativa (ocurre cuando
 * el HDMI entra en standby) y recupera la reproducción automáticamente.
 *
 * Solo de instancia cuando DeviceTypeHelper.detectDeviceType() == TELEVISOR.
 */
class FireTvVideoManager(
    private val videoView: VideoView,
    private val tag: String = "FireTvVideoManager"
) {

    var isSurfaceAlive: Boolean = false
        private set

    var onCompletion: (() -> Unit)? = null
    var onError: ((what: Int, extra: Int) -> Boolean)? = null
    var onPrepared: ((mp: MediaPlayer) -> Unit)? = null

    private var savedPosition: Int = 0
    private var pendingUri: Uri? = null
    private var callbackRegistered = false

    fun register() {
        if (callbackRegistered) return
        videoView.holder.addCallback(surfaceCallback)
        callbackRegistered = true
    }

    fun play(uri: Uri) {
        pendingUri = uri
        savedPosition = 0
        videoView.setOnCompletionListener { onCompletion?.invoke() }
        videoView.setOnPreparedListener { mp ->
            mp.setVideoScalingMode(MediaPlayer.VIDEO_SCALING_MODE_SCALE_TO_FIT)
            onPrepared?.invoke(mp)
        }
        videoView.setOnErrorListener { _, what, extra ->
            onError?.invoke(what, extra) ?: true
        }
        if (isSurfaceAlive) {
            videoView.setVideoURI(uri)
            videoView.start()
        } else {
            Log.w(tag, "play: surface no lista, pendiente uri=$uri")
        }
    }

    fun pause() {
        if (isSurfaceAlive) {
            savedPosition = videoView.currentPosition.coerceAtLeast(0)
            Log.d(tag, "pause: savedPosition=$savedPosition")
        }
        videoView.stopPlayback()
    }

    fun resume() {
        if (isSurfaceAlive && pendingUri != null) {
            videoView.setVideoURI(pendingUri)
            videoView.seekTo(savedPosition)
            videoView.start()
            Log.i(tag, "resume: desde posicion $savedPosition")
        }
    }

    fun release() {
        videoView.stopPlayback()
        videoView.setOnCompletionListener(null)
        videoView.setOnPreparedListener(null)
        videoView.setOnErrorListener(null)
        pendingUri = null
        savedPosition = 0
    }

    fun currentPosition(): Int = if (isSurfaceAlive) videoView.currentPosition.coerceAtLeast(0) else savedPosition

    fun duration(): Int = if (isSurfaceAlive) videoView.duration.coerceAtLeast(0) else 0

    private val surfaceCallback = object : SurfaceHolder.Callback {
        override fun surfaceCreated(holder: SurfaceHolder) {
            isSurfaceAlive = true
            Log.i(tag, "surfaceCreated — recuperando si hay pendiente")
            if (pendingUri != null) {
                videoView.setVideoURI(pendingUri)
                if (savedPosition > 0) videoView.seekTo(savedPosition)
                videoView.start()
                Log.i(tag, "surfaceCreated: recuperado desde posicion $savedPosition")
            }
        }

        override fun surfaceChanged(holder: SurfaceHolder, format: Int, w: Int, h: Int) {}

        override fun surfaceDestroyed(holder: SurfaceHolder) {
            Log.w(tag, "surfaceDestroyed — salvando posicion")
            savedPosition = videoView.currentPosition.coerceAtLeast(0)
            isSurfaceAlive = false
            videoView.stopPlayback()
        }
    }
}
