package com.example.verificadordepreciosluz.util

import android.net.Uri
import android.util.Log
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView

class PlayerManager(
    private val playerView: PlayerView,
    private val tag: String = "PlayerManager"
) {

    var onCompletion: (() -> Unit)? = null
    var onError: ((what: Int, extra: Int) -> Boolean)? = null

    private var exoPlayer: ExoPlayer? = null
    private var currentUri: Uri? = null

    private val playerListener = object : Player.Listener {
        override fun onPlaybackStateChanged(state: Int) {
            when (state) {
                Player.STATE_ENDED -> {
                    Log.d(tag, "Reproducción finalizada naturalmente")
                    onCompletion?.invoke()
                }
            }
        }

        override fun onPlayerError(error: PlaybackException) {
            Log.w(tag, "Error de reproducción: errorCode=${error.errorCode} ${error.message}")
            onError?.invoke(1, error.errorCode) ?: true
        }
    }

    fun play(uri: Uri) {
        currentUri = uri

        val player = ExoPlayer.Builder(playerView.context).build()
        exoPlayer?.release()
        exoPlayer = player

        player.setMediaItem(MediaItem.fromUri(uri))
        player.prepare()
        player.playWhenReady = true
        player.addListener(playerListener)
        playerView.player = player

        Log.d(tag, "play: $uri")
    }

    fun pause() {
        exoPlayer?.pause()
        Log.d(tag, "pause")
    }

    fun resume() {
        exoPlayer?.play()
        Log.d(tag, "resume")
    }

    fun release() {
        exoPlayer?.stop()
        exoPlayer?.removeListener(playerListener)
        exoPlayer?.release()
        exoPlayer = null
        playerView.player = null
        currentUri = null
        Log.d(tag, "release")
    }

    fun currentPosition(): Int = exoPlayer?.currentPosition?.toInt() ?: 0

    fun duration(): Int = exoPlayer?.duration?.toInt() ?: 0

    fun isPlaying(): Boolean = exoPlayer?.isPlaying ?: false
}
