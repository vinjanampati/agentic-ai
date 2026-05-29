package com.example.demo.model;

public class Order {
    private String id;
    private String productId;
    private int quantity;
    private String customerName;
    private String status;
    private double total;

    public Order() {}

    public Order(String id, String productId, int quantity, String customerName, String status, double total) {
        this.id = id;
        this.productId = productId;
        this.quantity = quantity;
        this.customerName = customerName;
        this.status = status;
        this.total = total;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getProductId() { return productId; }
    public void setProductId(String productId) { this.productId = productId; }

    public int getQuantity() { return quantity; }
    public void setQuantity(int quantity) { this.quantity = quantity; }

    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public double getTotal() { return total; }
    public void setTotal(double total) { this.total = total; }
}
