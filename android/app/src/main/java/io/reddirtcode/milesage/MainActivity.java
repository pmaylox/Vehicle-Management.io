package io.reddirtcode.milesage;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.ContentValues;
import android.content.Intent;
import android.content.IntentSender;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.core.content.FileProvider;
import androidx.webkit.WebViewAssetLoader;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.IOException;
import java.util.UUID;

import org.json.JSONObject;
import com.google.mlkit.vision.documentscanner.GmsDocumentScannerOptions;
import com.google.mlkit.vision.documentscanner.GmsDocumentScanning;
import com.google.mlkit.vision.documentscanner.GmsDocumentScanningResult;
import java.io.OutputStream;

public class MainActivity extends Activity {
    private static final int FILE_CHOOSER_CODE = 218;
    private static final int SERVICE_DOCUMENT_SCAN_CODE = 219;
    private boolean serviceScanOpen = false;
    private WebView web;
    private ValueCallback<Uri[]> pendingFileChooser;
    private Uri cameraUri;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(android.graphics.Color.rgb(20,42,64));
        web = new WebView(this);
        setContentView(web);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setMediaPlaybackRequiresUserGesture(true);
        final WebViewAssetLoader assets = new WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
            .build();
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assets.shouldInterceptRequest(request.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if ("appassets.androidplatform.net".equals(uri.getHost())) return false;
                if ("http".equals(uri.getScheme()) || "https".equals(uri.getScheme())) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) {}
                }
                return true;
            }
            @Override public void onPageFinished(WebView view, String url) {
                // The mobile app uses Blob URL downloads for JSON backups and receipt photos.
                // WebView cannot save blob: URLs using DownloadManager; hand them to a
                // restricted Android bridge writing only into public MileSage Downloads.
                String hook = "(function(){if(window.__milesageDownloadHook)return;window.__milesageDownloadHook=true;" +
                    "const prior=HTMLAnchorElement.prototype.click;" +
                    "HTMLAnchorElement.prototype.click=function(){var a=this;" +
                    "if(a.download&&a.href.startsWith('blob:')){" +
                    "fetch(a.href).then(r=>r.blob()).then(b=>{var f=new FileReader();" +
                    "f.onloadend=function(){var s=String(f.result);MileSageAndroid.saveBase64(a.download,b.type||'application/octet-stream',s.split(',')[1]);};" +
                    "f.readAsDataURL(b);}).catch(e=>alert('Download failed: '+e.message));return;}" +
                    "return prior.apply(a,arguments);};})();";
                view.evaluateJavascript(hook, null);
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (pendingFileChooser != null) pendingFileChooser.onReceiveValue(null);
                pendingFileChooser = callback;
                cameraUri = null;
                try {
                    Intent base = params.createIntent();
                    boolean imageInput = false;
                    for (String accept : params.getAcceptTypes()) {
                        if (accept != null && accept.contains("image")) imageInput = true;
                    }
                    Intent chooser = Intent.createChooser(base, imageInput ? "Take or choose receipt photo" : "Choose MileSage file");
                    if (imageInput) {
                        File dir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
                        if (dir != null) {
                            File file = File.createTempFile("milesage_receipt_", ".jpg", dir);
                            cameraUri = FileProvider.getUriForFile(MainActivity.this,
                                getPackageName()+".fileprovider",file);
                            Intent capture = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
                            capture.putExtra(MediaStore.EXTRA_OUTPUT,cameraUri);
                            capture.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                            chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, new android.os.Parcelable[]{capture});
                        }
                    }
                    startActivityForResult(chooser, FILE_CHOOSER_CODE);
                } catch (Exception e) {
                    pendingFileChooser.onReceiveValue(null);
                    pendingFileChooser = null;
                    showToast("File picker unavailable");
                }
                return true;
            }
        });
        web.setDownloadListener((url, userAgent, contentDisposition, mimeType, length) -> {
            if (!url.startsWith("https://")) { showToast("Use the MileSage download controls"); return; }
            try {
                DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                request.setTitle(URLUtil.guessFileName(url,contentDisposition,mimeType));
                request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,
                    URLUtil.guessFileName(url,contentDisposition,mimeType));
                ((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(request);
            } catch (Exception e) { showToast("Download failed"); }
        });
        web.addJavascriptInterface(new DownloadBridge(), "MileSageAndroid");
        web.loadUrl("https://appassets.androidplatform.net/assets/index.html");
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == SERVICE_DOCUMENT_SCAN_CODE) {
            serviceScanOpen = false;
            if (resultCode != RESULT_OK) {
                serviceScanResult(null, "Scan cancelled. No service record changed.");
                return;
            }
            try {
                GmsDocumentScanningResult scan = GmsDocumentScanningResult.fromActivityResultIntent(data);
                if (scan == null || scan.getPdf() == null || scan.getPdf().getPageCount() < 1) {
                    throw new IOException("No PDF pages returned.");
                }
                File directory = new File(getFilesDir(), "service_invoices");
                if (!directory.exists() && !directory.mkdirs()) throw new IOException("Cannot create PDF folder.");
                String id = UUID.randomUUID().toString();
                File file = new File(directory, id + ".pdf");
                try (InputStream in = getContentResolver().openInputStream(scan.getPdf().getUri());
                     OutputStream out = new FileOutputStream(file)) {
                    if (in == null) throw new IOException("Cannot open scanner PDF.");
                    byte[] buf = new byte[32 * 1024];
                    int n;
                    long total = 0;
                    while ((n = in.read(buf)) != -1) {
                        total += n;
                        if (total > 30_000_000) throw new IOException("PDF exceeds 30 MB.");
                        out.write(buf, 0, n);
                    }
                    if (total < 100) throw new IOException("Scanned PDF is empty.");
                } catch (Exception e) {
                    file.delete();
                    throw e;
                }
                JSONObject payload = new JSONObject();
                payload.put("id", id);
                payload.put("pages", scan.getPdf().getPageCount());
                payload.put("name", "MileSage-Service-" + id + ".pdf");
                serviceScanResult(payload, null);
            } catch (Exception e) {
                serviceScanResult(null, "Could not save scanned PDF: " + e.getMessage());
            }
            return;
        }
        if (requestCode == FILE_CHOOSER_CODE && pendingFileChooser != null) {
            Uri[] result = null;
            if (resultCode == RESULT_OK) {
                if (data != null) result = WebChromeClient.FileChooserParams.parseResult(resultCode,data);
                if ((result == null || result.length == 0) && cameraUri != null) result = new Uri[]{cameraUri};
            }
            pendingFileChooser.onReceiveValue(result);
            pendingFileChooser = null;
            cameraUri = null;
        }
    }

    private void showToast(String message) {
        runOnUiThread(() -> Toast.makeText(this,message,Toast.LENGTH_LONG).show());
    }


    private void serviceScanResult(JSONObject data, String error) {
        try {
            JSONObject payload = data == null ? new JSONObject() : data;
            if (error != null) payload.put("error", error);
            if (web != null) {
                String js = "if(window.milesageServiceScannerComplete)window.milesageServiceScannerComplete(" +
                    payload.toString() + ");";
                runOnUiThread(() -> web.evaluateJavascript(js, null));
            }
        } catch (Exception ignored) {
            showToast("Unable to report document scanner result.");
        }
    }

    private void beginServiceDocumentScan() {
        if (serviceScanOpen) return;
        serviceScanOpen = true;
        try {
            GmsDocumentScannerOptions options = new GmsDocumentScannerOptions.Builder()
                .setGalleryImportAllowed(true)
                .setPageLimit(30)
                .setResultFormats(GmsDocumentScannerOptions.RESULT_FORMAT_PDF)
                .setScannerMode(GmsDocumentScannerOptions.SCANNER_MODE_FULL)
                .build();
            GmsDocumentScanning.getClient(options).getStartScanIntent(this)
                .addOnSuccessListener(intentSender -> {
                    try {
                        startIntentSenderForResult(intentSender, SERVICE_DOCUMENT_SCAN_CODE,
                            null, 0, 0, 0);
                    } catch (IntentSender.SendIntentException e) {
                        serviceScanOpen = false;
                        serviceScanResult(null, "Unable to start document scanner: " + e.getMessage());
                    }
                })
                .addOnFailureListener(error -> {
                    serviceScanOpen = false;
                    serviceScanResult(null, "Scanner unavailable: " + error.getMessage());
                });
        } catch (Exception error) {
            serviceScanOpen = false;
            serviceScanResult(null, "Scanner unavailable: " + error.getMessage());
        }
    }

    private void openSavedServiceDocument(String id) {
        if (id == null || !id.matches("[a-f0-9-]{36}")) {
            showToast("Invalid service document reference.");
            return;
        }
        File file = new File(new File(getFilesDir(), "service_invoices"), id + ".pdf");
        if (!file.isFile()) {
            showToast("This service PDF is not on this device. Keep the original PDF when moving phones.");
            return;
        }
        try {
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", file);
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, "application/pdf");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(intent, "Open service invoice"));
        } catch (Exception e) {
            showToast("No compatible PDF viewer installed.");
        }
    }

    private void shareSavedServiceDocument(String id) {
        if (id == null || !id.matches("[a-f0-9-]{36}")) {
            showToast("Invalid service document reference.");return;
        }
        File pdf = new File(new File(getFilesDir(), "service_invoices"), id + ".pdf");
        if (!pdf.isFile()) {showToast("Scanned service PDF not found on this device.");return;}
        try {
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", pdf);
            Intent intent = new Intent(Intent.ACTION_SEND);
            intent.setType("application/pdf");
            intent.putExtra(Intent.EXTRA_STREAM,uri);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(intent,"Save or share service PDF"));
        } catch (Exception e) {
            showToast("Unable to share service document.");
        }
    }

    private class DownloadBridge {
        @JavascriptInterface public void scanServiceInvoice() {
            runOnUiThread(() -> beginServiceDocumentScan());
        }
        @JavascriptInterface public void openServiceInvoice(String id) {
            runOnUiThread(() -> openSavedServiceDocument(id));
        }
        @JavascriptInterface public void shareServiceInvoice(String id) {
            runOnUiThread(() -> shareSavedServiceDocument(id));
        }

        @JavascriptInterface public void saveBase64(String filename, String mimeType, String base64) {
            // Only printable safe filenames, never arbitrary filesystem paths.
            String name = filename == null ? "MileSage-backup.json" :
                filename.replaceAll("[^A-Za-z0-9._-]", "_");
            if (name.length() > 100) name = name.substring(0,100);
            if (name.isEmpty() || name.equals(".") || name.equals("..")) name = "MileSage-backup.json";
            String mime = mimeType != null && mimeType.startsWith("image/") ? mimeType :
                (name.endsWith(".json") ? "application/json" : "application/octet-stream");
            try {
                if (base64 == null || base64.length() > 32000000) throw new IllegalArgumentException("File too large");
                byte[] bytes = Base64.decode(base64, Base64.DEFAULT);
                if (bytes.length > 24000000) throw new IllegalArgumentException("File too large");
                boolean photo = mime.startsWith("image/");
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues values = new ContentValues();
                    values.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
                    values.put(MediaStore.MediaColumns.MIME_TYPE, mime);
                    values.put(MediaStore.MediaColumns.RELATIVE_PATH,
                        Environment.DIRECTORY_DOWNLOADS + (photo ? "/MileSage/Photos" : "/MileSage"));
                    Uri dest = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                    if (dest == null) throw new IllegalStateException("Cannot create download");
                    try (OutputStream stream = getContentResolver().openOutputStream(dest)) {
                        if (stream == null) throw new IllegalStateException("Cannot open download");
                        stream.write(bytes);
                    }
                } else {
                    File base = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
                    if (base == null) throw new IllegalStateException("Downloads unavailable");
                    File directory = new File(base,photo ? "MileSage/Photos" : "MileSage");
                    if (!directory.exists() && !directory.mkdirs()) throw new IllegalStateException("Cannot create folder");
                    try (FileOutputStream stream = new FileOutputStream(new File(directory,name))) {
                        stream.write(bytes);
                    }
                }
                showToast("Saved to Downloads/MileSage" + (photo ? "/Photos" : ""));
            } catch (Exception e) { showToast("MileSage save failed: "+e.getMessage()); }
        }
    }

    @Override public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }
    @Override protected void onDestroy() {
        if (web != null) web.destroy();
        super.onDestroy();
    }
}
