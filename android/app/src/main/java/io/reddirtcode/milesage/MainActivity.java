package io.reddirtcode.milesage;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.ContentValues;
import android.content.Intent;
import android.content.IntentSender;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.pdf.PdfRenderer;
import android.os.ParcelFileDescriptor;
import android.database.Cursor;
import android.provider.OpenableColumns;
import java.io.FileInputStream;
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
import java.util.List;

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
    private static final int EXPENSE_DOCUMENT_SCAN_CODE = 222;
    private static final int EXPENSE_PDF_IMPORT_CODE = 223;
    private static final int FUEL_GALLERY_PHOTO_CODE = 224;
    private boolean fuelGalleryPhotoOpen = false;
    private boolean pendingExpensePdfHistoryImport = false;
    private boolean expenseScanOpen = false;
    private boolean serviceReceiptScanOpen = false;
    private boolean fuelScanOpen = false;
    private boolean serviceScanOpen = false;
    private WebView web;
    private ValueCallback<Uri[]> pendingFileChooser;
    private Uri cameraUri;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(android.graphics.Color.rgb(41,39,36));
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

        if (requestCode == FUEL_GALLERY_PHOTO_CODE) {
            fuelGalleryPhotoOpen = false;
            if (resultCode != RESULT_OK) {
                fuelScanResult(null, null, "Saved photo selection cancelled. No fuel entry changed.");
                return;
            }
            Uri selected = data == null ? null : data.getData();
            if (selected == null) {
                fuelScanResult(null, null, "No saved photo was returned. Try another image.");
                return;
            }
            try {
                InputImage image = InputImage.fromFilePath(this, selected);
                TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
                recognizer.process(image)
                    .addOnSuccessListener(found -> {
                        try {
                            fuelScanResult(found.getText(), fuelScanPreview(selected), null);
                        } catch (Exception error) {
                            fuelScanResult(found.getText(), null,
                                "Receipt text was read, but its photo could not be attached: " + error.getMessage());
                        }
                    })
                    .addOnFailureListener(error -> {
                        try {
                            fuelScanResult("", fuelScanPreview(selected),
                                "Saved photo OCR failed: " + error.getMessage() + ". Enter fuel details manually.");
                        } catch (Exception imageError) {
                            fuelScanResult(null, null,
                                "Saved receipt photo could not be opened: " + imageError.getMessage());
                        }
                    })
                    .addOnCompleteListener(task -> recognizer.close());
            } catch (Exception error) {
                fuelScanResult(null, null, "Unable to read selected photo: " + error.getMessage());
            }
            return;
        }
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
        if (requestCode == EXPENSE_DOCUMENT_SCAN_CODE) {
            expenseScanOpen = false;
            if (resultCode != RESULT_OK) {
                expenseScanResult(null, "Scan cancelled. No expense record changed.");
                return;
            }
            try {
                GmsDocumentScanningResult scan = GmsDocumentScanningResult.fromActivityResultIntent(data);
                if (scan == null || scan.getPdf() == null || scan.getPdf().getPageCount() < 1) {
                    throw new IOException("No PDF pages returned.");
                }
                File directory = new File(getFilesDir(), "expense_invoices");
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
                payload.put("name", "MileSage-Expense-" + id + ".pdf");
                payload.put("ocr_pending", scan.getPages() != null && !scan.getPages().isEmpty());
                expenseScanResult(payload, null); // Show the PDF and draft buttons immediately.
                if (scan.getPages() != null && !scan.getPages().isEmpty()) {
                    beginExpensePagesOCR(scan.getPages(), id);
                } else {
                    expenseOcrResult(id, "", 0, "Scanner returned PDF without readable page images.");
                }
            } catch (Exception e) {
                expenseScanResult(null, "Could not save scanned PDF: " + e.getMessage());
            }
            return;
        }
        if (requestCode == EXPENSE_PDF_IMPORT_CODE) {
            final boolean forHistory = pendingExpensePdfHistoryImport;
            pendingExpensePdfHistoryImport = false;
            if (resultCode != RESULT_OK || data == null || data.getData() == null) {
                expensePdfImportResult(null, "PDF selection cancelled. No record changed.", forHistory);
                return;
            }
            final Uri uri = data.getData();
            new Thread(() -> {
                try {
                    // ContentResolver reads the user-selected document without
                    // asking for broad storage access. Never trust a file path.
                    File folder = new File(getFilesDir(), "expense_invoices");
                    if (!folder.exists() && !folder.mkdirs())
                        throw new IOException("Cannot create expense PDF folder.");
                    String id = UUID.randomUUID().toString();
                    File target = new File(folder, id + ".pdf");
                    int pages;
                    try {
                        try (InputStream input = getContentResolver().openInputStream(uri);
                             OutputStream output = new FileOutputStream(target)) {
                            if (input == null) throw new IOException("Could not open selected PDF.");
                            byte[] buffer = new byte[32768]; long count = 0;
                            int n;
                            while ((n = input.read(buffer)) != -1) {
                                count += n;
                                if (count > 30_000_000L) throw new IOException("PDF exceeds 30 MB.");
                                output.write(buffer, 0, n);
                            }
                            if (count < 100) throw new IOException("PDF was empty.");
                        }
                        try (FileInputStream first = new FileInputStream(target)) {
                            byte[] signature = new byte[5];
                            if (first.read(signature) != 5 ||
                                !"%PDF-".equals(new String(signature, java.nio.charset.StandardCharsets.US_ASCII)))
                                throw new IOException("Selected file is not a valid PDF.");
                        }
                        try (ParcelFileDescriptor descriptor = ParcelFileDescriptor.open(target, ParcelFileDescriptor.MODE_READ_ONLY);
                             PdfRenderer renderer = new PdfRenderer(descriptor)) {
                            pages = renderer.getPageCount();
                            if (pages < 1 || pages > 30)
                                throw new IOException("Choose a PDF containing 1 to 30 pages.");
                        }
                    } catch (Exception error) {
                        target.delete();throw error;
                    }
                    String name = "MileSage-Expense-" + id + ".pdf";
                    try (Cursor cursor = getContentResolver().query(uri,
                            new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
                        if (cursor != null && cursor.moveToFirst()) {
                            String supplied = cursor.getString(0);
                            if (supplied != null && supplied.toLowerCase(java.util.Locale.US).endsWith(".pdf")) {
                                supplied = supplied.replaceAll("[^A-Za-z0-9._ -]", "_").trim();
                                if (!supplied.isEmpty()) name = supplied.substring(0,Math.min(supplied.length(),120));
                            }
                        }
                    } catch (Exception ignored) { /* Keep safe generated name. */ }
                    JSONObject payload = new JSONObject();
                    payload.put("id",id);
                    payload.put("pages",pages);
                    payload.put("name",name);
                    payload.put("imported",true);
                    // Imported PDFs should use the same editable OCR suggestions as fresh scans.
                    // Reattached history documents do not mutate already-saved records.
                    payload.put("ocr_pending",!forHistory);
                    expensePdfImportResult(payload,null,forHistory);
                    if (!forHistory) readImportedExpensePdf(target,id);
                } catch (Exception error) {
                    expensePdfImportResult(null,"Unable to load PDF: "+error.getMessage(),forHistory);
                }
            },"MileSageExpensePDFImport").start();
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


    private void expenseScanResult(JSONObject data, String error) {
        try {
            JSONObject payload = data == null ? new JSONObject() : data;
            if (error != null) payload.put("error", error);
            if (web != null) {
                String js = "if(window.milesageExpenseScannerComplete)window.milesageExpenseScannerComplete(" +
                    payload.toString() + ");";
                runOnUiThread(() -> web.evaluateJavascript(js, null));
            }
        } catch (Exception ignored) {
            showToast("Unable to report document scanner result.");
        }
    }



    // The document scanner returns JPEG page URIs when both formats are requested.
    // Recognize sequentially, avoiding a full multi-page bitmap in memory.
    // If OCR fails, the PDF remains saved and can still be viewed/exported.
    private void expenseOcrResult(String id, String text, int pagesRead, String error) {
        try {
            JSONObject payload = new JSONObject();
            payload.put("id", id);
            payload.put("text", text);
            payload.put("ocr_pages", pagesRead);
            if (error != null) payload.put("error", error);
            String js = "if(window.milesageExpenseOCRComplete)window.milesageExpenseOCRComplete(" +
                payload.toString() + ");";
            runOnUiThread(() -> {
                if (web != null) web.evaluateJavascript(js, null);
            });
        } catch (Exception ignored) {
            showToast("Unable to return expense OCR text.");
        }
    }

    // ACTION_OPEN_DOCUMENT returns a PDF, not scanner JPEG pages. Rasterize each
    // validated page at a bounded resolution and use bundled offline ML Kit OCR.
    // The PDF remains attached even if OCR finds nothing; never store OCR text in JSON.
    // Called from the existing import worker (not the Android UI thread).
    private void readImportedExpensePdf(File pdf, String id) {
        StringBuilder all = new StringBuilder();
        int pagesRead = 0, failures = 0;
        String error = null;
        TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
        try (ParcelFileDescriptor fd = ParcelFileDescriptor.open(pdf, ParcelFileDescriptor.MODE_READ_ONLY);
             PdfRenderer renderer = new PdfRenderer(fd)) {
            for (int i = 0; i < renderer.getPageCount(); i++) {
                Bitmap bitmap = null;
                try (PdfRenderer.Page page = renderer.openPage(i)) {
                    float scale = Math.min(2.5f, Math.min(
                        2000f / Math.max(1, page.getWidth()),
                        2000f / Math.max(1, page.getHeight())));
                    int width = Math.max(1, Math.round(page.getWidth() * scale));
                    int height = Math.max(1, Math.round(page.getHeight() * scale));
                    bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
                    bitmap.eraseColor(android.graphics.Color.WHITE);
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                } catch (Exception renderError) {
                    failures++;
                    if (bitmap != null) bitmap.recycle();
                    continue;
                }
                try {
                    com.google.mlkit.vision.text.Text recognized =
                        com.google.android.gms.tasks.Tasks.await(
                            recognizer.process(InputImage.fromBitmap(bitmap, 0)));
                    pagesRead++;
                    String pageText = recognized.getText();
                    if (pageText != null && !pageText.trim().isEmpty() && all.length() < 48000) {
                        all.append("\n--- PAGE ").append(i + 1).append(" ---\n");
                        int room = Math.max(0, 48000 - all.length());
                        all.append(pageText, 0, Math.min(pageText.length(), room));
                    }
                } catch (Exception ocrError) {
                    failures++;
                } finally {
                    bitmap.recycle();
                }
            }
        } catch (Exception readError) {
            error = "Unable to read imported PDF: " + readError.getMessage();
        } finally {
            recognizer.close();
        }
        if (error == null && failures > 0)
            error = "Some PDF pages could not be recognized; verify the fields manually.";
        if (error == null && all.toString().trim().isEmpty())
            error = "No readable text found in this PDF; enter the expense fields manually.";
        expenseOcrResult(id, all.toString(), pagesRead, error);
    }

    private void beginExpensePagesOCR(List<GmsDocumentScanningResult.Page> pages, String id) {
        if (pages == null || pages.isEmpty()) {
            expenseOcrResult(id, "", 0, "No scanned page images were returned.");
            return;
        }
        TextRecognizer recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
        recognizeExpensePage(pages, 0, id, new StringBuilder(), recognizer, 0);
    }

    private void recognizeExpensePage(List<GmsDocumentScanningResult.Page> pages, int index,
            String id, StringBuilder all, TextRecognizer recognizer, int pagesRead) {
        if (index >= pages.size()) {
            recognizer.close();
            expenseOcrResult(id, all.toString(), pagesRead,
                pagesRead < pages.size() ? "Some pages could not be read; review manually." : null);
            return;
        }
        try {
            InputImage image = InputImage.fromFilePath(this, pages.get(index).getImageUri());
            recognizer.process(image)
                .addOnSuccessListener(result -> {
                    if (all.length() < 48000) {
                        String text = result.getText();
                        all.append("\n--- PAGE ").append(index + 1).append(" ---\n");
                        all.append(text.substring(0, Math.min(text.length(),
                            Math.max(0, 48000 - all.length()))));
                    }
                    recognizeExpensePage(pages, index + 1, id, all, recognizer, pagesRead + 1);
                })
                .addOnFailureListener(error ->
                    recognizeExpensePage(pages, index + 1, id, all, recognizer, pagesRead));
        } catch (Exception error) {
            recognizeExpensePage(pages, index + 1, id, all, recognizer, pagesRead);
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

    private void beginFuelGalleryPhotoPicker() {
        if (fuelGalleryPhotoOpen || fuelScanOpen) return;
        fuelGalleryPhotoOpen = true;
        try {
            Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            picker.addCategory(Intent.CATEGORY_OPENABLE);
            picker.setType("image/*");
            picker.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivityForResult(picker, FUEL_GALLERY_PHOTO_CODE);
        } catch (Exception error) {
            fuelGalleryPhotoOpen = false;
            fuelScanResult(null, null, "Unable to open saved photo picker: " + error.getMessage());
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


    // Open Android's Files picker, including PDFs exported by earlier MileSage
    // installations. The selected PDF is copied into THIS app's private store.
    private void beginExpensePdfImport(boolean forHistory) {
        try {
            Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            picker.setType("application/pdf");
            picker.addCategory(Intent.CATEGORY_OPENABLE);
            picker.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            pendingExpensePdfHistoryImport = forHistory;
            startActivityForResult(picker, EXPENSE_PDF_IMPORT_CODE);
        } catch (Exception error) {
            pendingExpensePdfHistoryImport = false;
            expensePdfImportResult(null,"Cannot open PDF file picker: "+error.getMessage(),forHistory);
        }
    }
    private void expensePdfImportResult(JSONObject payload, String error, boolean forHistory) {
        if (!forHistory) {expenseScanResult(payload,error);return;}
        try {
            JSONObject result = payload == null ? new JSONObject() : payload;
            if (error != null) result.put("error",error);
            String js = "if(window.milesageExpenseHistoryImportComplete)window.milesageExpenseHistoryImportComplete("+
                result.toString()+");";
            runOnUiThread(() -> {if(web != null)web.evaluateJavascript(js,null);});
        } catch (Exception ignored) {
            showToast("Unable to report imported expense PDF.");
        }
    }

    private void beginExpenseDocumentScan() {
        if (expenseScanOpen) return;
        expenseScanOpen = true;
        try {
            GmsDocumentScannerOptions options = new GmsDocumentScannerOptions.Builder()
                .setGalleryImportAllowed(true)
                .setPageLimit(30)
                .setResultFormats(GmsDocumentScannerOptions.RESULT_FORMAT_PDF, GmsDocumentScannerOptions.RESULT_FORMAT_JPEG)
                .setScannerMode(GmsDocumentScannerOptions.SCANNER_MODE_FULL)
                .build();
            GmsDocumentScanning.getClient(options).getStartScanIntent(this)
                .addOnSuccessListener(intentSender -> {
                    try {
                        startIntentSenderForResult(intentSender, EXPENSE_DOCUMENT_SCAN_CODE,
                            null, 0, 0, 0);
                    } catch (IntentSender.SendIntentException e) {
                        expenseScanOpen = false;
                        expenseScanResult(null, "Unable to start document scanner: " + e.getMessage());
                    }
                })
                .addOnFailureListener(error -> {
                    expenseScanOpen = false;
                    expenseScanResult(null, "Scanner unavailable: " + error.getMessage());
                });
        } catch (Exception error) {
            expenseScanOpen = false;
            expenseScanResult(null, "Scanner unavailable: " + error.getMessage());
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


    private void openSavedExpenseDocument(String id) {
        if (id == null || !id.matches("[a-f0-9-]{36}")) {
            showToast("Invalid expense document reference.");
            return;
        }
        File file = new File(new File(getFilesDir(), "expense_invoices"), id + ".pdf");
        if (!file.isFile()) {
            showToast("This expense PDF is not on this device. Keep the original PDF when moving phones.");
            return;
        }
        try {
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", file);
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, "application/pdf");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(intent, "Open expense document"));
        } catch (Exception e) {
            showToast("No compatible PDF viewer installed.");
        }
    }

    private void shareSavedExpenseDocument(String id) {
        if (id == null || !id.matches("[a-f0-9-]{36}")) {
            showToast("Invalid expense document reference.");return;
        }
        File pdf = new File(new File(getFilesDir(), "expense_invoices"), id + ".pdf");
        if (!pdf.isFile()) {showToast("Scanned expense PDF not found on this device.");return;}
        try {
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", pdf);
            Intent intent = new Intent(Intent.ACTION_SEND);
            intent.setType("application/pdf");
            intent.putExtra(Intent.EXTRA_STREAM,uri);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(intent,"Save or share expense PDF"));
        } catch (Exception e) {
            showToast("Unable to share expense document.");
        }
    }



    // Explicitly export a copy to Samsung My Files > Downloads > MileSage > Expenses.
    // The app-private original stays attached to Expense History.
    private void exportExpenseDocument(String id) {
        if (id == null || !id.matches("[a-f0-9-]{36}")) {
            showToast("Invalid expense PDF reference.");
            return;
        }
        File source = new File(new File(getFilesDir(), "expense_invoices"), id + ".pdf");
        if (!source.isFile()) {
            showToast("Expense PDF not found in this MileSage installation.");
            return;
        }
        final String name = "MileSage-Expense-" + id + ".pdf";
        Uri dest = null;
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                ContentValues values = new ContentValues();
                values.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
                values.put(MediaStore.MediaColumns.MIME_TYPE, "application/pdf");
                values.put(MediaStore.MediaColumns.RELATIVE_PATH,
                    Environment.DIRECTORY_DOWNLOADS + "/MileSage/Expenses");
                values.put(MediaStore.MediaColumns.IS_PENDING, 1);
                dest = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                if (dest == null) throw new IOException("Cannot create Downloads PDF.");
                try (InputStream input = new java.io.FileInputStream(source);
                     OutputStream output = getContentResolver().openOutputStream(dest)) {
                    if (output == null) throw new IOException("Cannot write Downloads PDF.");
                    byte[] buffer = new byte[32768];
                    int count;
                    while ((count = input.read(buffer)) > 0) output.write(buffer, 0, count);
                }
                ContentValues done = new ContentValues();
                done.put(MediaStore.MediaColumns.IS_PENDING, 0);
                getContentResolver().update(dest, done, null, null);
            } else {
                // Older Android: use the system share/save chooser rather than
                // requiring broad storage permissions.
                shareSavedExpenseDocument(id);
                return;
            }
            showToast("Saved: My Files > Downloads > MileSage > Expenses");
        } catch (Exception error) {
            if (dest != null) getContentResolver().delete(dest, null, null);
            showToast("Could not save Expense PDF: " + error.getMessage());
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
        @JavascriptInterface public void chooseFuelReceiptPhoto() {
            runOnUiThread(() -> beginFuelGalleryPhotoPicker());
        }
        @JavascriptInterface public void scanFuelReceipt() {
            runOnUiThread(() -> beginFuelDocumentScan());
        }
        @JavascriptInterface public void scanServiceReceipt() {
            runOnUiThread(() -> beginServiceReceiptScan());
        }
        @JavascriptInterface public void chooseExpensePdfFile(boolean forHistory) {
            runOnUiThread(() -> beginExpensePdfImport(forHistory));
        }
        @JavascriptInterface public void scanExpenseDocument() {
            runOnUiThread(() -> beginExpenseDocumentScan());
        }
        @JavascriptInterface public void openExpenseDocument(String id) {
            runOnUiThread(() -> openSavedExpenseDocument(id));
        }
        @JavascriptInterface public void shareExpenseDocument(String id) {
            runOnUiThread(() -> shareSavedExpenseDocument(id));
        }
        @JavascriptInterface public void saveExpenseDocument(String id) {
            runOnUiThread(() -> exportExpenseDocument(id));
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
