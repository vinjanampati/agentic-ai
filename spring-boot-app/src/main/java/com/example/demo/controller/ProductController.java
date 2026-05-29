package com.example.demo.controller;

import com.example.demo.model.Product;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    // In-memory store seeded with sample data
    private static final Map<String, Product> products = new LinkedHashMap<>();

    static {
        products.put("1", new Product("1", "Laptop Pro 15", 1299.99, "Electronics", 25));
        products.put("2", new Product("2", "Wireless Headphones", 149.99, "Electronics", 80));
        products.put("3", new Product("3", "Ergonomic Chair", 449.99, "Furniture", 15));
        products.put("4", new Product("4", "Stainless Water Bottle", 24.99, "Kitchen", 200));
        products.put("5", new Product("5", "Notebook Set", 9.99, "Stationery", 500));
    }

    @GetMapping
    public Collection<Product> getAllProducts() {
        return products.values();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Product> getProduct(@PathVariable String id) {
        Product product = products.get(id);
        if (product == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(product);
    }

    @PostMapping
    public Product createProduct(@RequestBody Product product) {
        String id = String.valueOf(products.size() + 1);
        product.setId(id);
        products.put(id, product);
        return product;
    }

    @GetMapping("/category/{category}")
    public List<Product> getByCategory(@PathVariable String category) {
        List<Product> result = new ArrayList<>();
        for (Product p : products.values()) {
            if (p.getCategory().equalsIgnoreCase(category)) {
                result.add(p);
            }
        }
        return result;
    }
}
