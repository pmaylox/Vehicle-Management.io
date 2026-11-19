package io.reddirtcode.milesage;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.ContentValues;
import android.content.Intent;
import android.content.IntentSender;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
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
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.IOException;
import java.util.UUID;

import org.json.JSONObject;
import com.google.mlkit.vision.documentscanner.GmsDocumentScannerOptions;
import com.google.mlkit.vision.documentscanner.GmsDocumentScanning;
import com.google.mlkit.vision.documentscanner.GmsDocumentScanningResult;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;
import java.io.OutputStream;

public class MainActivity extends Activity {
    private static final int FILE_CHOOSER_CODE = 218;
    private static final int SERVICE_DOCUMENT_SCAN_CODE = 219;
    private static final int FUEL_DOCUMENT_SCAN_CODE = 220;
    private static final int SERVICE_RECEIPT_SCAN_CODE = 221;
    private boolean serviceReceiptScanOpen = false;
    private boolean fuelScanOpen = false;
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
                    Intent chooser = Intent.createChooser(base, imageInput ? "Take or choose photo" : "Choose MileSage file");
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

        if (requestCode == FUEL_DOCUMENT_SCAN_CODE) {
            fuelScanOpen = false;
            if (resultCode != RESULT_OK) {
                fuelScanResult(null, null, "Fuel scan cancelled. No entry changed.");
                return;
            }
            try {
                GmsDocumentScanningResult scan = GmsDocumentScanningResult.fromActivityResultIntent(data);
                if (scan == null || scan.getPages() == null || scan.getPages().isEmpty())
                    throw new IOException("Scanner did not return a receipt image.");
                Uri receipt = scan.getPages().get(0).getImageUri();
                // Recognize the full-resolution, cropped and deskewed scanner page
                // BEFORE scaling a separate photo copy for the attached preview.
                InputImage image = InputImage.fromFilePath(this, receipt);
                TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
                recognizer.process(image)
                    .addOnSuccessListener(found -> {
                        try {
                            fuelScanResult(found.getText(), fuelScanPreview(receipt), null);
                        } catch (Exception error) {
                            fuelScanResult(found.getText(), null,
                                "Photo preview failed: " + error.getMessage());
                        } finally {
                            recognizer.close();
                        }
                    })
                    .addOnFailureListener(error -> {
                        recognizer.close();
                        try {
                            fuelScanResult("", fuelScanPreview(receipt),
                                "Text recognition failed. Enter fuel details manually.");
                        } catch (Exception imageError) {
                            fuelScanResult(null, null,
                                "Unable to read receipt photo: " + imageError.getMessage());
                        }
                    });
            } catch (Exception error) {
                fuelScanResult(null, null, "Fuel scanner could not finish: " + error.getMessage());
            }
            return;
        }
        if (requestCode == SERVICE_RECEIPT_SCAN_CODE) {
            serviceReceiptScanOpen = false;
            if (resultCode != RESULT_OK) {
                serviceReceiptScanResult(null, null, "Service receipt scan cancelled. No record changed.");
                return;
            }
            try {
                GmsDocumentScanningResult scan = GmsDocumentScanningResult.fromActivityResultIntent(data);
                if (scan == null || scan.getPages() == null || scan.getPages().isEmpty())
                    throw new IOException("No service receipt image returned.");
                Uri receipt = scan.getPages().get(0).getImageUri();
                InputImage image = InputImage.fromFilePath(this, receipt);
                TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
                recognizer.process(image)
                    .addOnSuccessListener(found -> {
                        try {
                            serviceReceiptScanResult(found.getText(), fuelScanPreview(receipt), null);
                        } catch (Exception error) {
                            serviceReceiptScanResult(found.getText(), null,
                                "Service receipt preview failed: " + error.getMessage());
                        } finally {
                            recognizer.close();
                        }
                    })
                    .addOnFailureListener(error -> {
                        recognizer.close();
                        try {
                            serviceReceiptScanResult("", fuelScanPreview(receipt),
                                "Text recognition failed; enter service details manually.");
                        } catch (Exception imageError) {
                            serviceReceiptScanResult(null, null, "Could not read service receipt: " + imageError.getMessage());
                        }
                    });
            } catch (Exception error) {
                serviceReceiptScanResult(null, null, "Service receipt scanner failed: " + error.getMessage());
            }
            return;
        }
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


    // Fuel uses a dedicated one-page, crop-and-enhance document scanning flow.
    // This does not change the existing Service-only multipage PDF scanner.
    private void fuelScanResult(String text, String imageDataUrl, String error) {
        try {
            JSONObject payload = new JSONObject();
            if (text != null) payload.put("text", text);
            if (imageDataUrl != null) payload.put("image", imageDataUrl);
            if (error != null) payload.put("error", error);
            String script = "if(window.milesageFuelScanComplete)window.milesageFuelScanComplete("
                + payload.toString() + ");";
            runOnUiThread(() -> {
                if (web != null) web.evaluateJavascript(script, null);
            });
        } catch (Exception ignored) {
            showToast("Unable to report fuel scan result.");
        }
    }

    private String fuelScanPreview(Uri source) throws IOException {
        BitmapFactory.Options info = new BitmapFactory.Options();
        info.inJustDecodeBounds = true;
        try (InputStream in = getContentResolver().openInputStream(source)) {
            if (in == null) throw new IOException("Scanned image unavailable.");
            BitmapFactory.decodeStream(in, null, info);
        }
        if (info.outWidth < 1 || info.outHeight < 1)
            throw new IOException("Invalid scanned image.");
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inSampleSize = 1;
        while (Math.max(info.outWidth / options.inSampleSize,
                info.outHeight / options.inSampleSize) > 2200) options.inSampleSize *= 2;
        Bitmap sourceBitmap;
        try (InputStream in = getContentResolver().openInputStream(source)) {
            if (in == null) throw new IOException("Scanned image unavailable.");
            sourceBitmap = BitmapFactory.decodeStream(in, null, options);
        }
        if (sourceBitmap == null) throw new IOException("Could not decode scanned image.");
        Bitmap image = sourceBitmap;
        try {
            int maximum = Math.max(image.getWidth(), image.getHeight());
            if (maximum > 2000) {
                float ratio = 2000f / maximum;
                image = Bitmap.createScaledBitmap(sourceBitmap,
                    Math.max(1, Math.round(image.getWidth() * ratio)),
                    Math.max(1, Math.round(image.getHeight() * ratio)), true);
            }
            try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                if (!image.compress(Bitmap.CompressFormat.JPEG, 82, out))
                    throw new IOException("Could not encode receipt image.");
                byte[] bytes = out.toByteArray();
                if (bytes.length > 3_500_000)
                    throw new IOException("Receipt photo exceeds safe storage size.");
                return "data:image/jpeg;base64," + Base64.encodeToString(bytes, Base64.NO_WRAP);
            }
        } finally {
            if (image != sourceBitmap) image.recycle();
            sourceBitmap.recycle();
        }
    }

    private void beginFuelDocumentScan() {
        if (fuelScanOpen) return;
        fuelScanOpen = true;
        try {
            GmsDocumentScannerOptions options = new GmsDocumentScannerOptions.Builder()
                .setGalleryImportAllowed(true)
                .setPageLimit(1)
                .setResultFormats(GmsDocumentScannerOptions.RESULT_FORMAT_JPEG)
                .setScannerMode(GmsDocumentScannerOptions.SCANNER_MODE_FULL)
                .build();
            GmsDocumentScanning.getClient(options).getStartScanIntent(this)
                .addOnSuccessListener(intent -> {
                    try {
                        startIntentSenderForResult(intent, FUEL_DOCUMENT_SCAN_CODE,
                            null, 0, 0, 0);
                    } catch (IntentSender.SendIntentException e) {
                        fuelScanOpen = false;
                        fuelScanResult(null, null, "Unable to start fuel scanner.");
                    }
                })
                .addOnFailureListener(error -> {
                    fuelScanOpen = false;
                    fuelScanResult(null, null,
                        "Fuel scanner unavailable: " + error.getMessage()
                        + ". Choose photo to enter manually.");
                });
        } catch (Exception error) {
            fuelScanOpen = false;
            fuelScanResult(null, null,
                "Fuel scanner unavailable: " + error.getMessage());
        }
    }

    // One-page service OCR; separate from the thirty-page PDF scanner.
    private void serviceReceiptScanResult(String text, String photo, String error) {
        try {
            JSONObject payload = new JSONObject();
            if (text != null) payload.put("text", text);
            if (photo != null) payload.put("image", photo);
            if (error != null) payload.put("error", error);
            String script = "if(window.milesageServiceReceiptComplete)window.milesageServiceReceiptComplete("
                + payload.toString() + ");";
            runOnUiThread(() -> {
                if (web != null) web.evaluateJavascript(script, null);
            });
        } catch (Exception ignored) {
            showToast("Unable to return service receipt scan.");
        }
    }
    private void beginServiceReceiptScan() {
        if (serviceReceiptScanOpen) return;
        serviceReceiptScanOpen = true;
        try {
            GmsDocumentScannerOptions options = new GmsDocumentScannerOptions.Builder()
                .setGalleryImportAllowed(true)
                .setPageLimit(1)
                .setResultFormats(GmsDocumentScannerOptions.RESULT_FORMAT_JPEG)
                .setScannerMode(GmsDocumentScannerOptions.SCANNER_MODE_FULL)
                .build();
            GmsDocumentScanning.getClient(options).getStartScanIntent(this)
                .addOnSuccessListener(intent -> {
                    try {
                        startIntentSenderForResult(intent, SERVICE_RECEIPT_SCAN_CODE,
                            null, 0, 0, 0);
                    } catch (IntentSender.SendIntentException e) {
                        serviceReceiptScanOpen = false;
                        serviceReceiptScanResult(null, null, "Could not launch service receipt scanner.");
                    }
                }).addOnFailureListener(error -> {
                    serviceReceiptScanOpen = false;
                    serviceReceiptScanResult(null, null,
                        "Service receipt scanner unavailable: " + error.getMessage());
                });
        } catch (Exception error) {
            serviceReceiptScanOpen = false;
            serviceReceiptScanResult(null, null, "Service receipt scanner unavailable: " + error.getMessage());
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


    // The bundled Latin OCR model runs locally in this APK. JS passes only a
    // compressed receipt image; recognized text is returned to the same WebView.
    // No receipt or OCR result is uploaded to a server.
    private void receiptOcrResult(String requestId, String text, String error) {
        try {
            JSONObject data = new JSONObject();
            data.put("id", requestId);
            if (error != null) data.put("error", error);
            else data.put("text", text == null ? "" : text);
            String js = "if(window.milesageReceiptOcrComplete)window.milesageReceiptOcrComplete(" +
                data.toString() + ");";
            runOnUiThread(() -> {
                if (web != null) web.evaluateJavascript(js, null);
            });
        } catch (Exception ignored) {
            showToast("Could not report receipt OCR result.");
        }
    }

    private void recognizeReceiptOnDevice(String requestId, String base64) {
        if (requestId == null || !requestId.matches("[0-9]{1,12}")) return;
        try {
            if (base64 == null || base64.length() > 11_000_000) {
                throw new IllegalArgumentException("Receipt image exceeds scanner size limit.");
            }
            byte[] bytes = Base64.decode(base64, Base64.DEFAULT);
            if (bytes.length == 0 || bytes.length > 8_250_000) {
                throw new IllegalArgumentException("Invalid receipt image size.");
            }
            BitmapFactory.Options bounds = new BitmapFactory.Options();
            bounds.inJustDecodeBounds = true;
            BitmapFactory.decodeByteArray(bytes, 0, bytes.length, bounds);
            if (bounds.outWidth < 1 || bounds.outHeight < 1 ||
                (long) bounds.outWidth * bounds.outHeight > 9_000_000L) {
                throw new IllegalArgumentException("Receipt image dimensions are invalid.");
            }
            Bitmap image = BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
            if (image == null) throw new IllegalArgumentException("Receipt photo could not be opened.");
            TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
            try {
                recognizer.process(InputImage.fromBitmap(image, 0))
                    .addOnSuccessListener(result -> receiptOcrResult(requestId, result.getText(), null))
                    .addOnFailureListener(error -> receiptOcrResult(requestId, null,
                        "Android text recognition failed: " + error.getMessage()))
                    .addOnCompleteListener(task -> {
                        recognizer.close();
                        image.recycle();
                    });
            } catch (Exception exception) {
                recognizer.close();
                image.recycle();
                throw exception;
            }
        } catch (Exception error) {
            receiptOcrResult(requestId, null, error.getMessage());
        }
    }

    private class DownloadBridge {
        @JavascriptInterface public void recognizeReceipt(String requestId, String base64) {
            recognizeReceiptOnDevice(requestId, base64);
        }
        @JavascriptInterface public void scanFuelReceipt() {
            runOnUiThread(() -> beginFuelDocumentScan());
        }
        @JavascriptInterface public void scanServiceReceipt() {
            runOnUiThread(() -> beginServiceReceiptScan());
        }
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
