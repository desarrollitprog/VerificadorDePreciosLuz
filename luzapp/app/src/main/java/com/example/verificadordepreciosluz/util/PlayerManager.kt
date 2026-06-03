package com.example.verificadordepreciosluz.util

import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView

class PlayerManager(
    private val playerView: PlayerView,
    private val enableRecoveryTimeout: Boolean = false,
    private val recoveryCheckMs: Long = 5_000L,
    private val persistentPlayer: Boolean = false,
    private val tag: String = "PlayerManager"
) {

    var onCompletion: (() -> Unit)? = null
    var onError: ((what: Int, extra: Int) -> Boolean)? = null

    private var exoPlayer: ExoPlayer? = null
    private var currentUri: Uri? = null

    private val recoveryHandler = Handler(Looper.getMainLooper())
    private var lastCheckedPosition: Int = 0
    private val recoveryRunnable = object : Runnable {
        override fun run() {
            val player = exoPlayer ?: return
            if (!player.isPlaying) {
                recoveryHandler.postDelayed(this, recoveryCheckMs)
                return
            }
            val currentPos = player.currentPosition.toInt()
            if (currentPos <= lastCheckedPosition) {
                Log.w(tag, "Recovery: reproducción estancada en pos=$currentPos, forzando error")
                onError?.invoke(1, PlaybackException.ERROR_CODE_TIMEOUT) ?: true
            } else {
                lastCheckedPosition = currentPos
                recoveryHandler.postDelayed(this, recoveryCheckMs)
            }
        }
    }

    private val playerListener = object : Player.Listener {
        override fun onPlaybackStateChanged(state: Int) {
            when (state) {
                Player.STATE_ENDED -> {
                    cancelRecoveryWatchdog()
                    Log.d(tag, "Reproducción finalizada naturalmente")
                    onCompletion?.invoke()
                }
            }
        }

        override fun onPlayerError(error: PlaybackException) {
            cancelRecoveryWatchdog()
            Log.w(tag, "Error de reproducción: errorCode=${error.errorCode} ${error.message}")
            onError?.invoke(1, error.errorCode) ?: true
        }
    }

    fun play(uri: Uri) {
        currentUri = uri

        if (exoPlayer == null) {
            exoPlayer = ExoPlayer.Builder(playerView.context).build().apply {
                playWhenReady = true
                addListener(playerListener)
            }
        }
        val player = exoPlayer ?: return
        player.stop()
        player.setMediaItem(MediaItem.fromUri(uri))
        player.prepare()
        playerView.player = player
        playerView.setKeepScreenOn(true)
        player.setWakeMode(C.WAKE_MODE_LOCAL)

        if (enableRecoveryTimeout) {
            lastCheckedPosition = 0
            recoveryHandler.removeCallbacks(recoveryRunnable)
            recoveryHandler.postDelayed(recoveryRunnable, recoveryCheckMs)
        }

        Log.d(tag, "play: $uri")
    }

    fun pause() {
        cancelRecoveryWatchdog()
        exoPlayer?.pause()
        Log.d(tag, "pause")
    }

    fun resume() {
        exoPlayer?.play()
        if (enableRecoveryTimeout) {
            lastCheckedPosition = exoPlayer?.currentPosition?.toInt() ?: 0
            recoveryHandler.removeCallbacks(recoveryRunnable)
            recoveryHandler.postDelayed(recoveryRunnable, recoveryCheckMs)
        }
        Log.d(tag, "resume")
    }

    fun release() {
        cancelRecoveryWatchdog()
        if (persistentPlayer) {
            exoPlayer?.stop()
            playerView.player = null
        } else {
            exoPlayer?.removeListener(playerListener)
            exoPlayer?.stop()
            exoPlayer?.release()
            exoPlayer = null
            playerView.player = null
        }
        currentUri = null
        Log.d(tag, "release")
    }

    fun dispose() {
        cancelRecoveryWatchdog()
        exoPlayer?.removeListener(playerListener)
        exoPlayer?.stop()
        exoPlayer?.release()
        exoPlayer = null
        playerView.player = null
        currentUri = null
        Log.d(tag, "dispose")
    }

    fun currentPosition(): Int = exoPlayer?.currentPosition?.toInt() ?: 0

    fun duration(): Int = exoPlayer?.duration?.toInt() ?: 0

    fun isPlaying(): Boolean = exoPlayer?.isPlaying ?: false

    private fun cancelRecoveryWatchdog() {
        recoveryHandler.removeCallbacks(recoveryRunnable)
    }
}
