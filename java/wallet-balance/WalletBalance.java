// SPDX-License-Identifier: Apache-2.0
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.UUID;

public class WalletBalance {
  static String required(String name) {
    String value = System.getenv(name);
    if (value == null || value.isBlank()) throw new IllegalArgumentException("Set " + name);
    return value;
  }

  public static void main(String[] args) {
    try {
      String base = System.getenv().getOrDefault("API_BASE_URL", "https://api.sandbox.1-funnel.org");
      URI origin = URI.create(base);
      boolean loopback = "http".equals(origin.getScheme()) && "127.0.0.1".equals(origin.getHost());
      if ((!"https".equals(origin.getScheme()) && !loopback) || origin.getHost() == null
          || origin.getUserInfo() != null || origin.getQuery() != null || origin.getFragment() != null
          || !(origin.getPath().isEmpty() || "/".equals(origin.getPath()))) {
        throw new IllegalArgumentException("Use an HTTPS API origin, or loopback HTTP for offline tests");
      }
      String businessId = UUID.fromString(required("BUSINESS_ID")).toString();
      URI url = URI.create(base.replaceAll("/+$", "") + "/v1/businesses/" + businessId + "/wallet/balance");
      HttpRequest request = HttpRequest.newBuilder(url)
          .timeout(Duration.ofSeconds(15))
          .header("Authorization", "Bearer " + required("ACCESS_TOKEN"))
          .header("Accept", "application/json")
          .GET().build();
      HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10))
          .followRedirects(HttpClient.Redirect.NEVER).build();
      HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
      int http_status = response.statusCode();
      if (http_status != 200) {
        System.err.println("API HTTP " + http_status + "; request "
            + response.headers().firstValue("X-Request-Id").orElse("unknown"));
        System.exit(1);
      }
      // Show the snapshot as JSON. Keep currency amounts as decimal strings.
      System.out.println(response.body());
    } catch (Exception error) {
      if (error instanceof InterruptedException) Thread.currentThread().interrupt();
      System.err.println("Request failed. Check configuration, credentials and connectivity.");
      System.exit(1);
    }
  }
}
