package com.example.demo.controller;

import com.example.demo.model.Order;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private static final Map<String, Order> orders = new LinkedHashMap<>();
    private static int orderCounter = 1;

    @GetMapping
    public Collection<Order> getAllOrders() {
        return orders.values();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Order> getOrder(@PathVariable String id) {
        Order order = orders.get(id);
        if (order == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(order);
    }

    @PostMapping
    public ResponseEntity<?> createOrder(@RequestBody Map<String, Object> request) {
        String productId = (String) request.get("productId");
        Object qtyObj = request.get("quantity");
        Object priceObj = request.get("pricePerUnit");
        String customerName = (String) request.get("customerName");

        if (productId == null || qtyObj == null || customerName == null) {
            return ResponseEntity.badRequest().body(Map.of("error", "productId, quantity, and customerName are required"));
        }

        int quantity = ((Number) qtyObj).intValue();
        double pricePerUnit = priceObj != null ? ((Number) priceObj).doubleValue() : 0.0;

        String id = "ORD-" + String.format("%03d", orderCounter++);
        Order order = new Order(id, productId, quantity, customerName, "CONFIRMED", pricePerUnit * quantity);
        orders.put(id, order);

        return ResponseEntity.ok(order);
    }

    @PatchMapping("/{id}/cancel")
    public ResponseEntity<Order> cancelOrder(@PathVariable String id) {
        Order order = orders.get(id);
        if (order == null) {
            return ResponseEntity.notFound().build();
        }
        order.setStatus("CANCELLED");
        return ResponseEntity.ok(order);
    }
}
