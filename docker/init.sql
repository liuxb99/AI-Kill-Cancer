-- AI Kill Cancer 資料庫初始化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100),
    gender VARCHAR(10),
    birth_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS diagnoses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID REFERENCES patients(id),
    cancer_type VARCHAR(100),
    subtype VARCHAR(100),
    stage VARCHAR(50),
    diagnosis_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS treatments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID REFERENCES patients(id),
    treatment_type VARCHAR(100),
    drug_name VARCHAR(200),
    dosage VARCHAR(100),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);
