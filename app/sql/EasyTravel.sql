USE easytravel;

-- 독립테이블
CREATE TABLE `member` (
    `member_id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL,
    `email` VARCHAR(255) NOT NULL,
    `aceess_token` VARCHAR(255) NOT NULL,
    `refresh_token` VARCHAR(255) NOT NULL,
    `oauth` VARCHAR(255) NOT NULL,
    `nickname` VARCHAR(50) NULL,
    `sex` CHAR(10) NULL,
    `picture_url` VARCHAR(2083) NULL,
    `birth` DATE NULL,
    `address` VARCHAR(255) NULL,
    `zip` CHAR(10) NULL,
    `phone_number` VARCHAR(20) NULL,
    `voice` VARCHAR(255) NULL,
    `role` VARCHAR(10) NULL,
    `created_at` DATETIME NULL,
    `updated_at` DATETIME NULL
);

CREATE TABLE `plan` (
    `plan_id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `memberId` INT NULL,
    `plan_name` VARCHAR(255) NULL,
    `start_date` DATETIME NULL,
    `end_date` DATETIME NULL,
    `main_location` VARCHAR(50) NULL,
    `ages` INT NULL,
    `companion_count` INT NULL,
    `plan_concepts` INT NULL,
    `member_id` INT NOT null,
    CONSTRAINT `FK_plan_member` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`)
);

-- 카테고리: 관광지/숙소/맛집/카페
CREATE TABLE `spot_category` (
    `spot_category_id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `spot_categoty` VARCHAR(255) NOT NULL
);

CREATE TABLE `spot_tag` (
    `spot_tag_id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `spot_tag` VARCHAR(255) NOT NULL
);

-- 연결 테이블

CREATE TABLE `checklist` (
    `plan_id` INT NOT NULL PRIMARY KEY,
    `item` VARCHAR(255) NULL,
    `state` BOOL NULL,
    CONSTRAINT `FK_checklist_plan_id` FOREIGN KEY (`plan_id`) REFERENCES `plan` (`plan_id`)
);

CREATE TABLE `spot` (
    `spot_id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `kor_name` VARCHAR(255) NOT NULL,
    `eng_name` VARCHAR(255) NULL,
    `description` VARCHAR(255) NOT NULL,
    `address` VARCHAR(255) NOT NULL,
    `zip` CHAR(10) NOT NULL,
    `url` VARCHAR(2083) NULL,
    `image_url` VARCHAR(2083) NOT NULL,
    `map_url` VARCHAR(2083) NOT NULL,
    `likes` INT NULL,
    `satisfaction` FLOAT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    `spot_category_id` INT NOT NULL,
    `phone_number` VARCHAR(300) NULL,
    `business_status` BOOL NULL,
    `business_hours` VARCHAR(255) NULL,
	CONSTRAINT `FK_spot_category_id` FOREIGN KEY (`spot_category_id`) REFERENCES `spot_category` (`spot_category_id`)
);


-- 중간 테이블
CREATE TABLE `plan_spot_map` (
    `plan_id` INT NOT NULL,
    `spot_id` INT NOT NULL,
    CONSTRAINT `FK_map_plan_id` FOREIGN KEY (`plan_id`) REFERENCES `plan` (`plan_id`),
 	CONSTRAINT `FK_map_spot_id` FOREIGN KEY (`spot_id`) REFERENCES `spot` (`spot_id`)
);

CREATE TABLE `plan_spot_tag_map` (
    `spot_id` INT NOT NULL,
    `spot_tag_id` INT NOT NULL,
    CONSTRAINT `FK_tag_map_spot_id` FOREIGN KEY (`spot_id`) REFERENCES `spot` (`spot_id`),
  	CONSTRAINT `FK_tag_mpa_spot_tag_id` FOREIGN KEY (`spot_tag_id`) REFERENCES `spot_tag` (`spot_tag_id`)
);
