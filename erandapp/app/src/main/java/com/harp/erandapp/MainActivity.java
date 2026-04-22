package com.harp.erandapp;

import android.app.Activity;
import android.os.Bundle;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Keep the screen on while viewing the harp drawings.
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        WebView webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        // Enable pinch-zoom on the viewer panels.
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);

        // Enable Chrome-inspector debugging via adb.
        WebView.setWebContentsDebuggingEnabled(true);
        webView.setWebViewClient(new WebViewClient());

        webView.loadUrl("file:///android_asset/index.html");
    }
}
