package com.ebook.backend;

import com.fasterxml.jackson.databind.JsonNode;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.ActiveProfiles;
import static org.assertj.core.api.Assertions.assertThat;

/** 真实 Tomcat + 独立 MySQL 测试，检查原书城业务与新增功能的集成边界。 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class BookstoreIntegrationTest {
    @LocalServerPort
    private int port;
    @Autowired
    private TestRestTemplate rest;
    @org.springframework.beans.factory.annotation.Value("${app.jwt.secret}")
    private String jwtSecret;

    private String url(String path) {
        return "http://127.0.0.1:" + port + path;
    }

    @org.junit.jupiter.api.BeforeEach
    void useJdkHttpClientForPatchRequests() {
        rest.getRestTemplate().setRequestFactory(
                new org.springframework.http.client.JdkClientHttpRequestFactory());
    }

    private String token(String username, String password) {
        var response = rest.postForEntity(url("/api/v1/users/login"),
                Map.of("username", username, "password", password), JsonNode.class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getHeaders().get(HttpHeaders.SET_COOKIE)).isNull();
        return response.getBody().get("accessToken").asText();
    }

    private ResponseEntity<JsonNode> call(HttpMethod method, String path, String token, Object body) {
        var headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (token != null) {
            headers.setBearerAuth(token);
        }
        return rest.exchange(url(path), method, new HttpEntity<>(body, headers), JsonNode.class);
    }

    @Test
    void missingAndTamperedTokensAreRejectedWithoutCreatingSession() {
        assertThat(call(HttpMethod.GET, "/api/v1/books/1", null, null).getStatusCode().value()).isEqualTo(401);
        String jwt = token("DefaultUser", "123456");
        String[] parts = jwt.split("\\.");
        String forged = parts[0] + "." + parts[1] + "." + (parts[2].startsWith("A") ? "B" : "A") + parts[2].substring(1);
        assertThat(call(HttpMethod.GET, "/api/v1/books/1", forged, null).getStatusCode().value()).isEqualTo(401);
        assertThat(call(HttpMethod.GET, "/api/v1/books/1", jwt, null).getStatusCode().value()).isEqualTo(200);
        assertThat(call(HttpMethod.GET, "/api/v1/books/1", null, null).getStatusCode().value()).isEqualTo(401);
    }

    @Test
    void expiredJwtCannotAccessBooks() {
        byte[] keyBytes = java.util.Base64.getDecoder().decode(jwtSecret);
        String expired = io.jsonwebtoken.Jwts.builder()
                .subject("2").issuer("ebook-bookstore")
                .expiration(java.util.Date.from(java.time.Instant.now().minusSeconds(60)))
                .signWith(io.jsonwebtoken.security.Keys.hmacShaKeyFor(keyBytes))
                .compact();
        assertThat(call(HttpMethod.GET, "/api/v1/books/1", expired, null)
                .getStatusCode().value()).isEqualTo(401);
    }

    @Test
    void paginationAndFiltersMatchTheContract() {
        String jwt = token("DefaultUser", "123456");
        var page = call(HttpMethod.GET, "/api/v1/books?page=0&size=2", jwt, null);
        assertThat(page.getBody().get("items").size()).isEqualTo(2);
        assertThat(page.getBody().get("totalElements").asInt()).isGreaterThanOrEqualTo(10);
        var category = call(HttpMethod.GET, "/api/v1/books?category=算法", jwt, null).getBody();
        assertThat(category.get("items").size()).isEqualTo(1);
        assertThat(category.get("items").get(0).get("category").asText()).isEqualTo("算法");
        var isbn = call(HttpMethod.GET, "/api/v1/books?isbn=9783000000004", jwt, null).getBody();
        assertThat(isbn.get("items").get(0).get("id").asInt()).isEqualTo(4);
        assertThat(call(HttpMethod.GET, "/api/v1/books?page=-1", jwt, null).getStatusCode().value()).isEqualTo(400);
        assertThat(call(HttpMethod.GET, "/api/v1/books/999999", jwt, null).getStatusCode().value()).isEqualTo(404);
    }

    @Test
    void cannotForgeAnAdministratorOrAnotherUser() {
        String jwt = token("DefaultUser", "123456");
        assertThat(call(HttpMethod.GET, "/api/v1/cart/1", jwt, null).getStatusCode().value()).isEqualTo(403);
        assertThat(call(HttpMethod.GET, "/api/v1/users/admin/all?operatorId=1", jwt, null).getStatusCode().value()).isEqualTo(403);
        assertThat(call(HttpMethod.PATCH, "/api/v1/books/1/stock?operatorId=1", jwt, Map.of("stockQty", 5)).getStatusCode().value()).isEqualTo(403);
        assertThat(call(HttpMethod.GET, "/api/v1/cart/2", jwt, null).getStatusCode().value()).isEqualTo(200);
        assertThat(call(HttpMethod.GET, "/api/v1/orders/2", jwt, null).getStatusCode().value()).isEqualTo(200);
    }

    @Test
    void stockUpdateChangesTheActualBookAndCanBeRestored() {
        String jwt = token("admin", "admin123");
        int original = call(HttpMethod.GET, "/api/v1/books/4", jwt, null).getBody().get("stockQty").asInt();
        try {
            var updated = call(HttpMethod.PATCH, "/api/v1/books/4/stock", jwt, Map.of("stockQty", 37));
            assertThat(updated.getStatusCode().value()).isEqualTo(200);
            assertThat(call(HttpMethod.GET, "/api/v1/books/4", jwt, null).getBody().get("stockQty").asInt()).isEqualTo(37);
            assertThat(call(HttpMethod.PATCH, "/api/v1/books/4/stock", jwt, Map.of("stockQty", -1)).getStatusCode().value()).isEqualTo(400);
        } finally {
            call(HttpMethod.PATCH, "/api/v1/books/4/stock", jwt, Map.of("stockQty", original));
        }
    }

    @Test
    void bookCreationUses201AndLocationAndDeletionUses204() {
        String jwt = token("admin", "admin123");
        var body = Map.of("title", "接口集成测试", "author", "Course", "price", 88,
                "category", "测试", "publisher", "课程", "isbn", "9787300000019",
                "format", "纸质书", "stockQty", 5, "description", "仅用于真实HTTP集成测试");
        var created = call(HttpMethod.POST, "/api/v1/books", jwt, body);
        assertThat(created.getStatusCode().value()).isEqualTo(201);
        String location = created.getHeaders().getFirst(HttpHeaders.LOCATION);
        assertThat(location).isEqualTo("/api/v1/books/" + created.getBody().get("id").asLong());
        assertThat(call(HttpMethod.DELETE, location, jwt, null).getStatusCode().value()).isEqualTo(204);
        assertThat(call(HttpMethod.GET, location, jwt, null).getStatusCode().value()).isEqualTo(404);
    }

    @Test
    void virtualThreadsHandleTwoHundredConcurrentDatabaseQueries() throws Exception {
        String jwt = token("DefaultUser", "123456");
        var runtime = rest.getForEntity(url("/api/v1/runtime"), JsonNode.class);
        assertThat(runtime.getBody().get("javaVersion").asText()).startsWith("21.");
        assertThat(runtime.getBody().get("requestThreadVirtual").asBoolean()).isTrue();
        try (HttpClient client = HttpClient.newHttpClient()) {
            var futures = new ArrayList<CompletableFuture<HttpResponse<String>>>();
            long start = System.nanoTime();
            for (int i = 0; i < 200; i++) {
                var request = HttpRequest.newBuilder(URI.create(url("/api/v1/books/1")))
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + jwt).GET().build();
                futures.add(client.sendAsync(request, HttpResponse.BodyHandlers.ofString()));
            }
            for (var future : futures) {
                var response = future.join();
                assertThat(response.statusCode()).isEqualTo(200);
                assertThat(response.headers().firstValue("X-Runtime-Thread")).contains("virtual-thread");
            }
            assertThat((System.nanoTime() - start) / 1_000_000).isLessThan(8000);
        }
    }
}
